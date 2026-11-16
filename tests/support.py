"""플레이어 테스트들이 함께 쓰는 도우미: 가짜 키 이벤트, 그리기를 기록하는 스프라이트, 한 프레임씩 진행."""

from typing import NamedTuple

from pico2d import SDL_KEYDOWN, SDL_KEYUP, SDLK_LSHIFT, SDLK_RSHIFT

import config
import resource
import stage_data
from camera import Camera
from player import Jump, Player

FRAME = 1 / 60
STAGE = stage_data.get_stage(2)
SHIFT_KEYS = (SDLK_LSHIFT, SDLK_RSHIFT)


class FakeEvent:
    def __init__(self, event_type, key=None):
        self.type = event_type
        self.key = key


class Draw(NamedTuple):
    name: str
    x: float
    y: float
    frame: int
    flip: bool
    alpha: float = 1.0


class RecordingSprite(resource.Sprite):
    """실제 manifest의 프레임 수·fps를 쓰되, 이미지는 그리지 않고 호출만 기록한다."""

    def __init__(self, info, draws):
        super().__init__(info, loader=lambda path: None)
        self._draws = draws

    def draw(self, x, y, frame=0, flip=False, scale=1, alpha=1.0):
        self._draws.append(Draw(self.info.name, x, y, int(frame), flip, alpha))


class SpriteBook:
    """Player의 sprite_lookup 자리에 꽂는 가짜 조회 함수."""

    def __init__(self):
        self.manifest = resource.load_manifest()
        self.draws = []

    def __call__(self, name):
        return RecordingSprite(self.manifest[name], self.draws)


def make_player(x=None, camera=None, book=None, **options):
    """(Player, 그리기 기록 장부). options는 Player 생성자에 그대로 넘긴다 (예: gauge=...).

    camera, book을 넘기면 다른 오브젝트(장애물 등)와 같은 카메라·장부를 함께 쓸 수 있다.
    """
    camera = camera if camera is not None else Camera(config.SCREEN_W, STAGE.length)
    book = book if book is not None else SpriteBook()
    player = Player(STAGE, camera, sprite_lookup=book, **options)
    if x is not None:
        player.x = float(x)
    return player, book


def press(player, key):
    player.handle_event(FakeEvent(SDL_KEYDOWN, key))


def release(player, key):
    player.handle_event(FakeEvent(SDL_KEYUP, key))


def run_for(player, seconds, dt=FRAME):
    for _ in range(round(seconds / dt)):
        player.step(dt)


def fly_until_landed(player, limit=200):
    """착지할 때까지 한 프레임씩 진행하고, 공중에 있던 프레임 수를 돌려준다."""
    steps = 0
    while player.state_machine.state is Jump:
        player.step(FRAME)
        steps += 1
        if steps > limit:
            raise AssertionError("점프가 끝나지 않았다")
    return steps


def state_of(player):
    return player.state_machine.state
