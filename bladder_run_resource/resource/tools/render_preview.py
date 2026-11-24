"""Offline raycaster preview of the 정왕역 platform, using exactly what the game can draw:
textured walls (DDA, perpendicular distance), flat floor/ceiling bands, z-buffered billboards, arms overlay.
"""
from PIL import Image, ImageDraw
import math, os, sys

OUT = os.path.join(os.path.dirname(__file__), 'out')
W, H, STRIP = 1280, 720, 2
FOV = math.radians(75); PROJ = (W / 2) / math.tan(FOV / 2)
WALL_H, EYE, FOG_K, SIDE = 3.0, 1.6, 0.035, 0.86   # morning: light haze, weak darkening
M_PER_PX = 0.014
CEIL_RGB, CEIL_DARK = (150, 144, 156), 0.18
FLOOR_RGB, FLOOR_DARK = (206, 202, 192), 0.15
ARMS_FW = 1260

def load(k): return Image.open(os.path.join(OUT, k + '.png')).convert('RGBA')
TEX = {k: load(k) for k in ['tex_psd_door_l', 'tex_psd_door_r', 'tex_psd_panel', 'tex_psd_train_l', 'tex_psd_train_r',
                            'tex_station_sign_1', 'tex_station_sign_2', 'tex_station_sign_3', 'tex_rail',
                            'tex_wall_tile', 'tex_wall_ad', 'tex_wall_sign_wc']}

def is_open(x, y):
    if 0 <= x < 40: return 0 <= y <= 5          # platform, 6 m wide
    if 40 <= x < 47: return 0 <= y <= 7         # gate area
    return False

def tex_for(x, y, frame=0):
    if y == -1 and 0 <= x < 40:                 # screen doors on the right
        if 17 <= x <= 19: return 'tex_station_sign_%d' % (20 - x)   # right wall reads toward -x
        k = ['door_l', 'door_r', 'panel'][x % 3]
        if x < 12 and k != 'panel': k = k.replace('door', 'train')
        return 'tex_psd_' + k
    if y == 6 and x < 40: return 'tex_rail'
    if x >= 47: return 'tex_wall_sign_wc' if y in (3, 4) else 'tex_wall_ad' if y == 1 else 'tex_wall_tile'
    return 'tex_wall_tile'

def shade(im, k):
    k = max(0.0, min(1.0, k))
    r, g, b, a = im.split()
    f = lambda v: int(v * k)
    return Image.merge('RGBA', (r.point(f), g.point(f), b.point(f), a))

def render(px, py, yaw, sprites, arms=('arms_walk', 0), out='preview_fp.png'):
    img = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(img)
    hz = H // 2
    # ceiling & floor bands (darker toward the horizon) - same trick as the game
    for i in range(8):
        t = i / 8
        c0 = tuple(int(v * (1 - CEIL_DARK * t)) for v in CEIL_RGB)
        f0 = tuple(int(v * (1 - FLOOR_DARK * t)) for v in FLOOR_RGB)
        d.rectangle([0, int(hz * t), W, int(hz * (t + 1 / 8))], fill=c0)
        d.rectangle([0, H - int(hz * (t + 1 / 8)), W, H - int(hz * t)], fill=f0)
    dx, dy = math.cos(yaw), math.sin(yaw)
    plx, ply = math.sin(yaw) * math.tan(FOV / 2), -math.cos(yaw) * math.tan(FOV / 2)   # camera plane -> screen right
    zbuf = []
    for i in range(W // STRIP):
        cam = 2 * (i + 0.5) / (W // STRIP) - 1
        rx, ry = dx + plx * cam, dy + ply * cam
        mx, my = math.floor(px), math.floor(py)
        ddx = abs(1 / rx) if rx else 1e30; ddy = abs(1 / ry) if ry else 1e30
        sx = 1 if rx > 0 else -1; sy = 1 if ry > 0 else -1
        sdx = (mx + 1 - px) * ddx if rx > 0 else (px - mx) * ddx
        sdy = (my + 1 - py) * ddy if ry > 0 else (py - my) * ddy
        while True:
            if sdx < sdy: sdx += ddx; mx += sx; side = 0
            else: sdy += ddy; my += sy; side = 1
            if not is_open(mx, my): break
        dist = (sdx - ddx) if side == 0 else (sdy - ddy)
        zbuf.append(dist)
        hit = (py + dist * ry) if side == 0 else (px + dist * rx)
        u = hit - math.floor(hit)
        if (side == 0 and rx > 0) or (side == 1 and ry < 0): u = 1 - u   # read textures left-to-right as seen from inside
        tk = tex_for(mx, my)
        tex = TEX[tk] if isinstance(tk, str) else TEX[tk[0]].crop((tk[1] * 96, 0, tk[1] * 96 + 96, 288))
        tu = min(tex.width - 1, int(u * tex.width))
        top = hz - (WALL_H - EYE) * PROJ / dist; hpx = WALL_H * PROJ / dist
        col = tex.crop((tu, 0, tu + 1, tex.height)).resize((STRIP, max(1, int(hpx))), Image.NEAREST)
        k = 1 / (1 + dist * FOG_K) * (SIDE if side == 1 else 1)
        _paste(img, shade(col, k), i * STRIP, int(top))
    # billboards, far -> near
    vis = []
    for (key, frame, fw, fh, wx, wy, flip) in sprites:
        rx, ry = wx - px, wy - py
        f = rx * dx + ry * dy
        l = rx * dy - ry * dx            # +: to the right of the view
        if f < 0.2: continue
        vis.append((f, l, key, frame, fw, fh, flip))
    for f, l, key, frame, fw, fh, flip in sorted(vis, reverse=True):
        sheet = load(key)
        im = sheet.crop((frame * fw, 0, frame * fw + fw, fh))
        if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        wh, ww = fh * M_PER_PX, fw * M_PER_PX
        hp, wp = wh * PROJ / f, ww * PROJ / f
        sxc = W / 2 + l / f * PROJ
        foot = hz + EYE * PROJ / f
        sim = shade(im.resize((max(1, int(wp)), max(1, int(hp))), Image.NEAREST), 1 / (1 + f * FOG_K))
        x0 = int(sxc - wp / 2); y0 = int(foot - hp)
        for c in range(0, sim.width, STRIP):
            col_i = (x0 + c) // STRIP
            if 0 <= col_i < len(zbuf) and f < zbuf[col_i]:
                _paste(img, sim.crop((c, 0, min(c + STRIP, sim.width), sim.height)), x0 + c, y0)
    if arms:
        a = load(arms[0]); fr = a.crop((arms[1] * ARMS_FW, 0, arms[1] * ARMS_FW + ARMS_FW, 300))
        img.alpha_composite(fr, (W // 2 - ARMS_FW // 2, H - 300))
    d = ImageDraw.Draw(img); d.rectangle([W // 2 - 2, hz - 2, W // 2 + 1, hz + 1], fill=(255, 255, 255, 200))
    img.convert('RGB').save(os.path.join(os.path.dirname(__file__), out))

def _paste(img, part, x, y):
    img.paste(part, (x, y), part)

if __name__ == '__main__':
    P = ('prop_pillar_pink', 0, 48, 216)
    B = ('prop_bench', 0, 120, 48)
    def npc(k, f, x, y, flip=False): return (k, f, 144, 144, x, y, flip)
    sprites = [P + (x, 3.6, False) for x in (18, 26, 34)] + [B + (x, 5.35, False) for x in (23, 31)]
    sprites += [npc('npc_commuter1_back', 1, 19.5, 1.9), npc('npc_traveler_back', 0, 23.5, 2.9),
                npc('npc_commuter3_back', 2, 28.0, 1.4), npc('npc_commuter2_back', 3, 31.5, 4.4, True)]
    render(13.0, 2.7, 0.0, sprites, ('arms_walk', 0), 'preview_fp.png')
