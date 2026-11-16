import unittest

import game_world


class Dummy:
    def __init__(self, bb=(0, 0, 10, 10)):
        self.bb = bb
        self.log = []

    def update(self):
        self.log.append("update")

    def draw(self):
        self.log.append("draw")

    def get_bb(self):
        return self.bb

    def handle_collision(self, group, other):
        self.log.append(("collision", group, other))


class GameWorldTest(unittest.TestCase):
    def setUp(self):
        game_world.clear()

    def tearDown(self):
        game_world.clear()

    def test_update_calls_every_object_once(self):
        a, b = Dummy(), Dummy()
        game_world.add_object(a, game_world.LAYER_PROP)
        game_world.add_object(b, game_world.LAYER_PLAYER)
        game_world.update()
        self.assertEqual(a.log, ["update"])
        self.assertEqual(b.log, ["update"])

    def test_render_draws_lower_layers_first(self):
        order = []

        class Marker(Dummy):
            def __init__(self, name):
                super().__init__()
                self.name = name

            def draw(self):
                order.append(self.name)

        game_world.add_object(Marker("fx"), game_world.LAYER_FX)
        game_world.add_object(Marker("bg"), game_world.LAYER_BACKGROUND)
        game_world.add_object(Marker("player"), game_world.LAYER_PLAYER)
        game_world.render()
        self.assertEqual(order, ["bg", "player", "fx"])

    def test_remove_object_removes_it_from_the_world_and_from_collision_pairs(self):
        a, b = Dummy(), Dummy()
        game_world.add_object(a, game_world.LAYER_PLAYER)
        game_world.add_object(b, game_world.LAYER_OBSTACLE)
        game_world.add_collision_pair("p:o", a, b)
        game_world.remove_object(b)
        game_world.update()
        game_world.handle_collisions()
        self.assertEqual(b.log, [])
        self.assertEqual(a.log, ["update"])

    def test_overlapping_boxes_notify_both_sides_with_group_and_other(self):
        a, b = Dummy((0, 0, 10, 10)), Dummy((5, 5, 15, 15))
        game_world.add_collision_pair("p:o", a, None)
        game_world.add_collision_pair("p:o", None, b)
        game_world.handle_collisions()
        self.assertEqual(a.log, [("collision", "p:o", b)])
        self.assertEqual(b.log, [("collision", "p:o", a)])

    def test_separated_boxes_do_not_collide(self):
        a, b = Dummy((0, 0, 10, 10)), Dummy((20, 0, 30, 10))
        game_world.add_collision_pair("p:o", a, None)
        game_world.add_collision_pair("p:o", None, b)
        game_world.handle_collisions()
        self.assertEqual(a.log, [])

    def test_boxes_that_only_touch_edges_do_not_collide(self):
        self.assertFalse(
            game_world.collide(Dummy((0, 0, 10, 10)), Dummy((10, 0, 20, 10)))
        )

    def test_object_with_no_box_is_ignored(self):
        a, b = Dummy((0, 0, 10, 10)), Dummy(None)
        game_world.add_collision_pair("p:o", a, None)
        game_world.add_collision_pair("p:o", None, b)
        game_world.handle_collisions()
        self.assertEqual(a.log, [])
        self.assertEqual(b.log, [])

    def test_object_removed_by_a_collision_callback_does_not_break_iteration(self):
        class Remover(Dummy):
            def handle_collision(self, group, other):
                game_world.remove_object(other)

        player = Remover((0, 0, 10, 10))
        first, second = Dummy((0, 0, 10, 10)), Dummy((0, 0, 10, 10))
        game_world.add_collision_pair("p:o", player, None)
        game_world.add_collision_pair("p:o", None, first)
        game_world.add_collision_pair("p:o", None, second)
        game_world.handle_collisions()
        self.assertEqual(len(first.log), 1)
        self.assertEqual(len(second.log), 1)

    def test_object_removed_earlier_in_the_pass_is_not_notified_later(self):
        class Remover(Dummy):
            def __init__(self, bb, victim):
                super().__init__(bb)
                self.victim = victim

            def handle_collision(self, group, other):
                super().handle_collision(group, other)
                game_world.remove_object(self.victim)

        first, second = Dummy((0, 0, 10, 10)), Dummy((0, 0, 10, 10))
        player = Remover((0, 0, 10, 10), second)
        game_world.add_collision_pair("p:o", player, None)
        game_world.add_collision_pair("p:o", None, first)
        game_world.add_collision_pair("p:o", None, second)
        game_world.handle_collisions()
        self.assertEqual(len(first.log), 1)
        self.assertEqual(second.log, [])

    def test_removing_an_object_twice_is_harmless(self):
        a = Dummy()
        game_world.add_object(a, game_world.LAYER_PROP)
        game_world.remove_object(a)
        game_world.remove_object(a)
        self.assertEqual(list(game_world.all_objects()), [])

    def test_all_objects_lists_every_layer(self):
        a, b = Dummy(), Dummy()
        game_world.add_object(a, game_world.LAYER_PROP)
        game_world.add_object(b, game_world.LAYER_FX)
        self.assertEqual(list(game_world.all_objects()), [a, b])

    def test_clear_empties_world_and_collision_pairs(self):
        a, b = Dummy(), Dummy()
        game_world.add_object(a, game_world.LAYER_PROP)
        game_world.add_collision_pair("p:o", a, b)
        game_world.clear()
        self.assertEqual(list(game_world.all_objects()), [])
        game_world.handle_collisions()
        self.assertEqual(a.log, [])


if __name__ == "__main__":
    unittest.main()
