"""BLADDER RUN - the goal: restroom entrance at the end of the corridor (x = 148, y = 0..6).
The end wall is drawn as ONE 7-tile picture (art 224x96) and sliced into 1 m tiles.
Facing +x, screen left = +y, so tile 1 (leftmost) goes on y = 6 and tile 7 on y = 0.
Tile 4 (y = 3, the corridor centre) is the goal door: tex_door_wc, 2 frames (closed / open).
"""
from PIL import Image, ImageDraw, ImageFont
import os, json

OUT = os.path.join(os.path.dirname(__file__), 'out')
S = 3
def hx(c):
    c = c.lstrip('#'); return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

TILE, TILE_L = hx('EAF2F6'), hx('CADAE2')          # restroom wall tiles
WAIN, WAIN_L = hx('9CC4DC'), hx('7EA8C4')          # lower blue tiles
NAVY, WHITE = hx('243256'), hx('F6F8FA')
MBLUE, WRED = hx('3C86C8'), hx('E0506E')
SOFFIT = hx('B8BCC4')

def pict_man(d, cx, top, s, c):
    """pictogram ~ (4s wide, 11s tall)."""
    d.ellipse([cx - s, top, cx + s, top + 2 * s], fill=c)
    d.rectangle([cx - 2 * s, top + 2 * s + 1, cx + 2 * s, top + 6 * s], fill=c)
    d.rectangle([cx - 2 * s, top + 6 * s, cx - 1, top + 11 * s], fill=c)
    d.rectangle([cx + 1, top + 6 * s, cx + 2 * s, top + 11 * s], fill=c)

def pict_woman(d, cx, top, s, c):
    d.ellipse([cx - s, top, cx + s, top + 2 * s], fill=c)
    d.polygon([(cx, top + 2 * s + 1), (cx - 3 * s, top + 8 * s), (cx + 3 * s, top + 8 * s)], fill=c)
    d.rectangle([cx - s, top + 2 * s + 1, cx + s, top + 4 * s], fill=c)
    d.rectangle([cx - s, top + 8 * s, cx - 1, top + 11 * s], fill=c)
    d.rectangle([cx + 1, top + 8 * s, cx + s, top + 11 * s], fill=c)

def wall(d, x0, x1):
    d.rectangle([x0, 0, x1, 95], fill=TILE)
    for y in range(24, 64, 8): d.line([(x0, y), (x1, y)], fill=TILE_L)
    for x in range(x0, x1 + 1, 8): d.line([(x, 24), (x, 63)], fill=TILE_L)
    d.rectangle([x0, 64, x1, 95], fill=WAIN)
    for y in range(64, 96, 8): d.line([(x0, y), (x1, y)], fill=WAIN_L)
    for x in range(x0 + 4, x1 + 1, 8): d.line([(x, 64), (x, 95)], fill=WAIN_L)
    d.rectangle([x0, 63, x1, 64], fill=hx('5E88A6'))                     # trim line
    d.rectangle([x0, 92, x1, 95], fill=hx('4E5662'))                     # skirting
    d.rectangle([x0, 0, x1, 5], fill=SOFFIT); d.line([(x0, 5), (x1, 5)], fill=hx('9A9EA6'))

def door_frame(d, x0):
    d.rectangle([x0 + 3, 27, x0 + 28, 95], fill=hx('8E969E'))
    d.rectangle([x0 + 3, 27, x0 + 28, 28], fill=hx('B8BEC6'))

def doorway_women(d, x0):
    door_frame(d, x0)
    d.rectangle([x0 + 5, 30, x0 + 26, 95], fill=hx('C9D4DC'))              # inside: partition wall, lit
    d.rectangle([x0 + 5, 30, x0 + 26, 34], fill=hx('F4F0E8'))
    d.rectangle([x0 + 5, 60, x0 + 26, 95], fill=hx('B4C2CC'))
    d.rectangle([x0 + 8, 34, x0 + 23, 59], fill=WHITE)                    # sign on partition
    pict_woman(d, x0 + 15, 36, 2, WRED)
    d.rectangle([x0 + 5, 90, x0 + 26, 95], fill=hx('A0AEB8'))

def door_men(d, x0, opened):
    door_frame(d, x0)
    if not opened:
        d.rectangle([x0 + 5, 30, x0 + 26, 95], fill=MBLUE)
        d.rectangle([x0 + 5, 30, x0 + 6, 95], fill=hx('2C6AA0'))
        d.rectangle([x0 + 9, 36, x0 + 22, 62], fill=WHITE)
        pict_man(d, x0 + 15, 38, 2, MBLUE)
        d.rectangle([x0 + 22, 68, x0 + 24, 74], fill=hx('E8ECF0'))          # push plate
    else:
        d.rectangle([x0 + 5, 30, x0 + 26, 95], fill=hx('FFF8E4'))           # bright interior
        for y in range(34, 88, 6): d.line([(x0 + 5, y), (x0 + 26, y)], fill=hx('F2E8CC'))
        for ux in (x0 + 8, x0 + 18):                                         # urinals
            d.rectangle([ux - 1, 55, ux + 6, 73], fill=hx('9AA6B2')); d.rectangle([ux, 56, ux + 5, 72], fill=WHITE)
            d.rectangle([ux + 1, 62, ux + 4, 70], fill=hx('C8D2DA'))
            d.rectangle([ux + 2, 52, ux + 3, 55], fill=hx('B8BEC6'))
        for i in range(3):                                                   # light rays spilling out
            d.line([(x0 + 8 + i * 6, 30), (x0 + 4 + i * 6, 95)], fill=hx('FFFDF2'))
        d.rectangle([x0 + 5, 30, x0 + 7, 95], fill=MBLUE)                   # door swung open, edge visible
        d.rectangle([x0 + 5, 88, x0 + 26, 95], fill=hx('E6DCC0'))

def door_accessible(d, x0):
    door_frame(d, x0)
    d.rectangle([x0 + 5, 30, x0 + 26, 95], fill=hx('C2C8D0'))
    d.line([(x0 + 15, 30), (x0 + 15, 95)], fill=hx('9AA2AA'))
    d.rectangle([x0 + 9, 38, x0 + 21, 50], fill=MBLUE)
    d.ellipse([x0 + 14, 39, x0 + 16, 41], fill=WHITE)                      # wheelchair pictogram
    d.line([(x0 + 15, 42), (x0 + 15, 46), (x0 + 18, 46), (x0 + 19, 49)], fill=WHITE)
    d.arc([x0 + 11, 43, x0 + 17, 49], 40, 300, fill=WHITE)
    d.rectangle([x0 + 23, 60, x0 + 25, 64], fill=hx('5AD27A'))              # open button

def compose(opened):
    im = Image.new('RGBA', (224, 96)); d = ImageDraw.Draw(im); d.fontmode = '1'
    wall(d, 0, 223)
    doorway_women(d, 32)
    # tile 3: pictogram pair plaque + mirror strip
    d.rectangle([69, 40, 90, 52], fill=WHITE); d.rectangle([69, 52, 90, 52], fill=hx('9AA2AA'))
    pict_woman(d, 75, 41, 1, WRED); d.line([(79, 42), (79, 50)], fill=hx('C8CED4')); pict_man(d, 84, 41, 1, MBLUE)
    door_men(d, 96, opened)
    # tile 5: hand dryer + tissue
    d.rectangle([134, 46, 146, 56], fill=hx('D8DCE0')); d.rectangle([134, 56, 146, 57], fill=hx('8E969E'))
    d.rectangle([138, 58, 142, 59], fill=hx('5A5E66'))
    d.rectangle([150, 50, 155, 56], fill=WHITE); d.rectangle([150, 50, 155, 50], fill=hx('B8BEC6'))
    door_accessible(d, 160)
    # big overhead sign over tiles 2..6
    d.rectangle([34, 7, 189, 23], fill=NAVY); d.rectangle([34, 23, 189, 23], fill=hx('101830'))
    pict_woman(d, 46, 9, 1, hx('FF8AA0')); pict_man(d, 56, 9, 1, hx('8EC8FF'))
    big = ImageFont.truetype(FONT, 13, index=1); small = ImageFont.truetype(FONT, 8, index=1)
    d.text((112, 14), '화장실', font=big, fill=WHITE, anchor='mm')
    d.text((162, 15), 'Restroom', font=small, fill=hx('C8D4F0'), anchor='mm')
    return im

def build():
    closed, opened = compose(False), compose(True)
    up = lambda im: im.resize((im.width * S, im.height * S), Image.NEAREST)
    manifest = {}
    for i in range(7):
        if i == 3: continue
        key = f'tex_wc_end_{i + 1}'
        up(closed.crop((i * 32, 0, i * 32 + 32, 96))).save(os.path.join(OUT, key + '.png'))
        manifest[key] = {'file': f'station/{key}.png', 'frame_w': 96, 'frame_h': 288, 'frames': 1}
    door = Image.new('RGBA', (64, 96))
    door.paste(closed.crop((96, 0, 128, 96)), (0, 0)); door.paste(opened.crop((96, 0, 128, 96)), (32, 0))
    up(door).save(os.path.join(OUT, 'tex_door_wc.png'))
    manifest['tex_door_wc'] = {'file': 'station/tex_door_wc.png', 'frame_w': 96, 'frame_h': 288, 'frames': 2}
    tile = Image.new('RGBA', (32, 96)); wall(ImageDraw.Draw(tile), 0, 31)
    up(tile).save(os.path.join(OUT, 'tex_wc_tile.png'))
    manifest['tex_wc_tile'] = {'file': 'station/tex_wc_tile.png', 'frame_w': 96, 'frame_h': 288, 'frames': 1}
    up(closed).save(os.path.join(os.path.dirname(__file__), 'wc_end_closed.png'))
    up(opened).save(os.path.join(os.path.dirname(__file__), 'wc_end_open.png'))
    return manifest

if __name__ == '__main__':
    m = build()
    json.dump(m, open(os.path.join(OUT, 'manifest_wc.json'), 'w'), ensure_ascii=False, indent=2)
    print(len(m), 'textures')
