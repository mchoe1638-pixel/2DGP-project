"""BLADDER RUN - first-person arms (view model).
Art grid 420x100, scaled x3 -> 1260x300 per frame (arms near 1/4 and 3/4 of a 1280 screen). Bottom edge = bottom of the screen.
Each arm is drawn upright as a pixel 'stamp' (sleeve + cuff + wrist + hand), then rotated
around its bottom-centre with NEAREST and pasted. In-game: frame = int(step_phase*2) % 4.
"""
from PIL import Image, ImageDraw
import os, json

OUT = os.path.join(os.path.dirname(__file__), 'out')
S, AW, AH = 3, 420, 100

def hx(c):
    c = c.lstrip('#'); return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)

SLEEVE, SLEEVE_S, FOLD = hx('FFF9E0'), hx('E6DCC0'), hx('D4C8A6')
CUFF, BUTTON = hx('EFE6CC'), hx('A89E80')
SKIN, SKIN_S, SKIN_D, SKIN_H = hx('F7C894'), hx('E2A878'), hx('C08050'), hx('FFDDB0')

def R(d, x0, y0, x1, y1, c): d.rectangle([x0, y0, x1, y1], fill=c)

def fist(d, cx, top):
    """back-of-hand fist, 28w x 24h, knuckles on top. thumb on viewer-left (inner side of a right arm)."""
    x0 = cx - 14
    R(d, x0+2, top+3, x0+27, top+23, SKIN)           # main block
    R(d, x0+1, top+6, x0+1, top+20, SKIN)
    R(d, x0+3, top+22, x0+26, top+23, SKIN_S)        # under-shadow
    R(d, x0+26, top+5, x0+27, top+22, SKIN_S)        # outer edge shade
    for i in range(4):                               # four knuckles
        kx = x0 + 3 + i*6
        R(d, kx, top+1, kx+4, top+4, SKIN)
        R(d, kx+1, top, kx+3, top, SKIN)
        R(d, kx+1, top+1, kx+2, top+2, SKIN_H)
        if i < 3:
            R(d, kx+5, top+3, kx+5, top+11, SKIN_D)  # crease between fingers
        R(d, kx+1, top+8, kx+3, top+8, SKIN_S)       # second joint line
    R(d, x0+3, top+12, x0+25, top+12, SKIN_S)        # curled finger tips line
    # thumb wrapping across the front, inner side
    R(d, x0-2, top+12, x0+8, top+19, SKIN)
    R(d, x0-2, top+19, x0+8, top+20, SKIN_S)
    R(d, x0-3, top+13, x0-3, top+18, SKIN_S)
    R(d, x0+6, top+13, x0+8, top+14, SKIN_H)
    R(d, x0+9, top+14, x0+9, top+18, SKIN_D)

def open_hand(d, cx, top):
    """open hand, fingers up, palm 24w; total 30w x 34h."""
    x0 = cx - 12
    lens = (11, 13, 12, 9)                           # index..little (viewer left -> right)
    for i, ln in enumerate(lens):
        fx = x0 + 1 + i*6
        ft = top + (13 - ln)
        R(d, fx, ft+1, fx+4, top+14, SKIN)
        R(d, fx+1, ft, fx+3, ft, SKIN)
        R(d, fx+4, ft+2, fx+4, top+14, SKIN_S)
        R(d, fx+1, ft+ln//2, fx+3, ft+ln//2, SKIN_S)  # joint
        R(d, fx+1, ft+1, fx+2, ft+1, SKIN_H)          # nail glint
    R(d, x0, top+13, x0+24, top+33, SKIN)            # palm
    R(d, x0+23, top+14, x0+24, top+32, SKIN_S)
    R(d, x0+2, top+31, x0+22, top+33, SKIN_S)
    R(d, x0+5, top+20, x0+12, top+20, SKIN_S)        # palm crease
    # thumb sticking out on the inner side
    R(d, x0-4, top+18, x0+1, top+28, SKIN)
    R(d, x0-7, top+14, x0-3, top+21, SKIN)
    R(d, x0-6, top+13, x0-4, top+13, SKIN)
    R(d, x0-7, top+20, x0-3, top+21, SKIN_S)

def stamp(length, hand):
    """upright right-side arm: bottom-centre at (W/2, H-1)."""
    W, H = 64, 140
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, bot = W // 2, H - 1
    wb, wt = 46, 32                                  # sleeve width bottom (near) / top (far)
    top = bot - length
    d.polygon([(cx-wb//2, bot), (cx+wb//2, bot), (cx+wt//2, top), (cx-wt//2, top)], fill=SLEEVE)
    d.polygon([(cx+wb//2-12, bot), (cx+wb//2, bot), (cx+wt//2, top), (cx+wt//2-8, top)], fill=SLEEVE_S)
    for k in range(2):                               # fabric folds
        fy = top + 10 + k*int(length*0.35)
        if fy < bot - 4:
            R(d, cx-8, fy, cx-1, fy, FOLD); R(d, cx-1, fy+1, cx+4, fy+1, FOLD)
    R(d, cx-wt//2-1, top-6, cx+wt//2+1, top, CUFF)   # cuff
    R(d, cx-wt//2-1, top, cx+wt//2+1, top, FOLD)
    R(d, cx+wt//2-5, top-4, cx+wt//2-4, top-3, BUTTON)
    R(d, cx-10, top-11, cx+10, top-6, SKIN)          # wrist
    R(d, cx+7, top-11, cx+10, top-6, SKIN_S)
    if hand == 'fist': fist(d, cx, top-33)
    else:              open_hand(d, cx, top-43)
    return im

def place(canvas, bx, by, angle, length, hand, side):
    """side: -1 viewer-left arm, +1 viewer-right arm. angle>0 leans toward screen centre."""
    st = stamp(length, hand)
    if side < 0:
        st = st.transpose(Image.FLIP_LEFT_RIGHT)
    W, H = st.size
    pad = Image.new('RGBA', (H*2, H*2), (0, 0, 0, 0))
    pad.paste(st, (H - W//2, 0))                     # bottom-centre of stamp -> pad centre
    rot = pad.rotate(angle * side, resample=Image.NEAREST)
    _paste(canvas, rot, int(bx - H), int(by - H))

def _paste(canvas, im, x, y):
    big = Image.new('RGBA', (AW + 600, AH + 600), (0, 0, 0, 0))
    big.paste(canvas, (300, 300))
    big.alpha_composite(im, (x + 300, y + 300))
    canvas.paste(big.crop((300, 300, 300 + AW, 300 + AH)), (0, 0))

def frame(left, right):
    c = Image.new('RGBA', (AW, AH), (0, 0, 0, 0))
    for spec, side in ((left, -1), (right, 1)):
        if spec is None: continue
        bx, by, ang, ln, hand = spec
        if side > 0: bx = AW - bx                    # specs are written for the left side, mirrored
        place(c, bx, by, ang, ln, hand, side)
    return c

# pose = (base_x measured from the arm's own screen edge, base_y (>100 = below screen), lean deg, sleeve length, hand)
IDLE0 = (96, 116, 10, 30, 'fist'); IDLE1 = (96, 118, 10, 30, 'fist')
W_FWD, W_MID, W_BACK = (104, 112, 26, 52, 'fist'), (98, 116, 14, 36, 'fist'), (92, 134, 4, 24, 'fist')
R_FWD, R_MID, R_BACK = (112, 110, 34, 64, 'fist'), (100, 116, 18, 38, 'fist'), (88, 160, 4, 20, 'fist')
ANIMS = {
    'arms_idle': [frame(IDLE0, IDLE0), frame(IDLE1, IDLE1)],
    'arms_walk': [frame(W_FWD, W_BACK), frame(W_MID, W_MID), frame(W_BACK, W_FWD), frame(W_MID, W_MID)],
    'arms_run':  [frame(R_FWD, R_BACK), frame(R_MID, R_MID), frame(R_BACK, R_FWD), frame(R_MID, R_MID)],
    'arms_jump': [frame((94, 112, 4, 64, 'open'), (94, 112, 4, 64, 'open')),
                  frame((82, 118, -6, 50, 'open'), (82, 118, -6, 50, 'open'))],
    'arms_hold': [   # left hand pressed on the stomach (low centre), right arm flailing at its side
        frame((176, 100, 74, 22, 'open'), (104, 112, 24, 54, 'fist')),
        frame((177, 101, 74, 22, 'open'), (98, 118, 12, 38, 'fist')),
        frame((176, 100, 74, 22, 'open'), (108, 110, 32, 58, 'open')),
        frame((175, 101, 74, 22, 'open'), (94, 120, 8, 32, 'fist')),
    ],
    'arms_fall': [frame((90, 112, -2, 64, 'open'), (90, 112, -2, 64, 'open')),
                  frame((96, 140, 12, 30, 'open'), (96, 140, 12, 30, 'open'))],
}

def build():
    manifest = {}
    for key, frames in ANIMS.items():
        sheet = Image.new('RGBA', (AW*S*len(frames), AH*S), (0, 0, 0, 0))
        for i, fr in enumerate(frames):
            sheet.paste(fr.resize((AW*S, AH*S), Image.NEAREST), (i*AW*S, 0))
        sheet.save(os.path.join(OUT, key + '.png'))
        manifest[key] = {'file': f'arms/{key}.png', 'frame_w': AW*S, 'frame_h': AH*S, 'frames': len(frames)}
    return manifest

if __name__ == '__main__':
    m = build()
    json.dump(m, open(os.path.join(OUT, 'manifest_arms.json'), 'w'), ensure_ascii=False, indent=2)
    print(len(m), 'sheets')
