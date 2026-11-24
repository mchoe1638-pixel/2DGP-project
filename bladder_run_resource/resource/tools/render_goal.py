"""Goal scene: last metres of the 연결통로, facing the restroom entrance (end wall x = 148)."""
import render_preview as rp
for k in ['tex_wc_end_1', 'tex_wc_end_2', 'tex_wc_end_3', 'tex_wc_end_5', 'tex_wc_end_6', 'tex_wc_end_7',
          'tex_door_wc', 'tex_wc_tile', 'tex_wall_stairs']:
    rp.TEX[k] = rp.load(k)
DOOR = {'f': 0}
def is_open(x, y): return 120 <= x < 148 and 0 <= y <= 6
def tex_for(x, y, frame=0):
    if x >= 148:
        if y == 3: return ('tex_door_wc', DOOR['f'])
        return 'tex_wc_end_%d' % (7 - y)          # y=6 -> tile 1 (leftmost)
    if x >= 145: return 'tex_wc_tile'
    if y == 7 and x in (136, 141): return 'tex_wall_sign_wc'
    if y == -1 and x % 4 == 1: return 'tex_wall_ad'
    return 'tex_wall_tile'
rp.is_open, rp.tex_for = is_open, tex_for
rp.CEIL_RGB, rp.CEIL_DARK = (214, 212, 208), 0.12          # indoor fluorescent ceiling
rp.FLOOR_RGB, rp.FLOOR_DARK = (196, 190, 180), 0.12
rp.FOG_K = 0.03
npc = lambda k, f, x, y, flip=False: (k, f, 144, 144, x, y, flip)
sprites = [npc('npc_commuter4_back', 1, 143.2, 4.6), npc('npc_commuter5_front', 0, 139.0, 1.4)]
rp.render(137.5, 3.5, 0.0, sprites, ('arms_hold', 0), 'preview_goal_closed.png')
DOOR['f'] = 1
rp.render(144.6, 3.5, 0.0, [], ('arms_jump', 0), 'preview_goal_open.png')
