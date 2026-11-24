"""BLADDER RUN - front-facing obstacle NPC sprites.
Art grid 48x48, scaled x3 -> 144x144 per frame, 2 frames per sheet (horizontal strip).
Feet sit 1 art px (=3 px) above the frame bottom, matching the existing player/NPC rule.
"""
from PIL import Image, ImageDraw
import os, json

OUT = os.path.join(os.path.dirname(__file__), 'out')
os.makedirs(OUT, exist_ok=True)
S = 3
G = 48

def hx(c):
    c = c.lstrip('#'); return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)

# palette shared with 김급해
SKIN, SKIN_S = hx('F7C894'), hx('E2A878')
EYE = hx('1A1233')
MOUTH = hx('8A3A2A')
WHITE, WHITE_S = hx('FFF9E0'), hx('E6DCC0')
SHOE = hx('2A2236')

class Px:
    def __init__(self):
        self.im = Image.new('RGBA', (G, G), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
    def r(self, x0, y0, x1, y1, c):          # inclusive rect
        if c is None: return
        self.d.rectangle([x0, y0, x1, y1], fill=c)
    def p(self, x, y, c):
        self.d.point((x, y), fill=c)
    def poly(self, pts, c):
        self.d.polygon(pts, fill=c)

def shade(c, k=0.82):
    return tuple(int(v * k) for v in c[:3]) + (255,)

# ---------------------------------------------------------------- body parts
def legs(g, pants, shoe=SHOE, skin_legs=False, skirt=None, dy=0):
    if skirt:
        g.r(15, 33+dy, 32, 38+dy, skirt); g.r(31, 33+dy, 32, 38+dy, shade(skirt))
        g.r(17, 39+dy, 21, 44, SKIN); g.r(26, 39+dy, 30, 44, SKIN)
        g.r(16, 45, 21, 46, shoe); g.r(26, 45, 31, 46, shoe)
        return
    c = SKIN if skin_legs else pants
    g.r(16, 33+dy, 31, 35+dy, pants)
    g.r(16, 36+dy, 22, 44, c); g.r(25, 36+dy, 31, 44, c)
    g.r(21, 36+dy, 22, 44, shade(c)); g.r(30, 36+dy, 31, 44, shade(c))
    g.r(15, 45, 22, 46, shoe); g.r(25, 45, 32, 46, shoe)

def torso(g, top, dy=0, wide=False):
    x0, x1 = (14, 33) if wide else (15, 32)
    g.r(x0, 19+dy, x1, 32+dy, top)
    g.r(x1-1, 20+dy, x1, 32+dy, shade(top))

def arm(g, side, sleeve, pose='down', dy=0, hand=SKIN):
    """side: 'L' viewer-left, 'R' viewer-right"""
    ax = 12 if side == 'L' else 33
    if pose == 'down':
        g.r(ax, 20+dy, ax+2, 30+dy, sleeve); g.r(ax, 31+dy, ax+2, 33+dy, hand)
    elif pose == 'raise':                      # hand up beside head
        hx0 = ax - 1 if side == 'L' else ax + 1
        g.r(ax, 17+dy, ax+2, 23+dy, sleeve)
        g.r(hx0, 11+dy, hx0+2, 16+dy, sleeve)
        g.r(hx0-1, 7+dy, hx0+3, 10+dy, hand)
    elif pose == 'wave':
        hx0 = ax - 3 if side == 'L' else ax + 3
        g.r(ax, 17+dy, ax+2, 23+dy, sleeve)
        g.r((ax+hx0)//2, 12+dy, (ax+hx0)//2+2, 17+dy, sleeve)
        g.r(hx0-1, 6+dy, hx0+3, 11+dy, hand)
    elif pose == 'chest':                      # forearm across the chest
        g.r(ax, 20+dy, ax+2, 26+dy, sleeve)
        if side == 'L': g.r(ax, 26+dy, 22, 28+dy, sleeve); g.r(20, 25+dy, 23, 29+dy, hand)
        else:           g.r(25, 26+dy, ax+2, 28+dy, sleeve); g.r(24, 25+dy, 27, 29+dy, hand)
    elif pose == 'out':                        # reaching toward the viewer: bigger hand, low centre
        g.r(ax, 20+dy, ax+2, 25+dy, sleeve)
        if side == 'L': g.r(ax+1, 25+dy, 21, 28+dy, sleeve); g.r(18, 26+dy, 24, 31+dy, hand)
        else:           g.r(26, 25+dy, ax+1, 28+dy, sleeve); g.r(23, 26+dy, 29, 31+dy, hand)

def head(g, hair, style='short', dy=0, look='front', mouth='flat', skin=SKIN):
    g.r(17, 6+dy, 30, 18+dy, skin)
    g.r(29, 7+dy, 30, 18+dy, shade(skin, .9))
    g.r(22, 19+dy, 25, 19+dy, skin)                       # neck
    hair_styles = {
        'short':  [(17, 4, 30, 8), (16, 5, 16, 11), (31, 5, 31, 9)],
        'side':   [(17, 4, 30, 7), (16, 5, 17, 11), (18, 8, 23, 8), (31, 5, 31, 8)],
        'bob':    [(16, 4, 31, 8), (15, 6, 17, 19), (30, 6, 32, 19)],
        'pony':   [(16, 4, 31, 8), (15, 6, 16, 14), (31, 6, 32, 14), (32, 9, 34, 17)],
        'curly':  [(15, 3, 32, 8), (14, 5, 16, 14), (31, 5, 33, 14)],
        'bald':   [(16, 9, 16, 14), (31, 9, 31, 14), (19, 6, 28, 6)],   # comb-over strands
        'none':   [],
    }
    for x0, y0, x1, y1 in hair_styles[style]:
        g.r(x0, y0+dy, x1, y1+dy, hair)
    if style == 'curly':      # curl texture
        for x in range(15, 33, 3): g.p(x, 3+dy, shade(hair, .8)); g.p(x+1, 8+dy, shade(hair, .8))
    ey = {'front': 12, 'down': 14, 'up': 10}[look]
    g.r(20, ey+dy, 21, ey+1+dy, EYE); g.r(26, ey+dy, 27, ey+1+dy, EYE)
    my = 16 + dy
    if mouth == 'flat':   g.r(23, my, 24, my, MOUTH)
    elif mouth == 'open': g.r(22, my-1, 25, my+1, MOUTH); g.r(23, my+1, 24, my+1, hx('E8605A'))
    elif mouth == 'grin': g.r(21, my-1, 26, my, MOUTH); g.r(22, my-1, 25, my-1, WHITE)
    elif mouth == 'o':    g.r(23, my-1, 24, my, MOUTH)
    elif mouth == 'frown':g.r(22, my, 25, my, MOUTH); g.p(22, my-1, SKIN); g.p(21, my+1, MOUTH); g.p(26, my+1, MOUTH)
    elif mouth == 'smile':g.r(22, my, 25, my, MOUTH); g.p(21, my-1, MOUTH); g.p(26, my-1, MOUTH)

def blush(g, dy=0):
    c = hx('F49A8A'); g.r(18, 14+dy, 19, 14+dy, c); g.r(28, 14+dy, 29, 14+dy, c)

# ---------------------------------------------------------------- characters
def tourist(f):
    g = Px(); dy = 0
    shirt, hat = hx('3FB8A8'), hx('E9D27A')
    legs(g, hx('C9B48A'), shoe=hx('8A5A3A'))
    g.r(16, 38, 22, 44, SKIN); g.r(25, 38, 31, 44, SKIN)          # shorts -> bare shins
    torso(g, shirt)
    for (x, y, c) in [(17,21,'FFD24A'),(24,23,'FF7A9A'),(29,21,'FFD24A'),(19,27,'FF7A9A'),(27,29,'FFD24A'),(22,30,'FF7A9A')]:
        g.r(x, y, x+1, y+1, hx(c))
    g.r(19, 19, 20, 24, hx('2D2340')); g.r(21, 24, 25, 27, hx('2D2340')); g.r(22, 25, 24, 26, hx('8FA4C0'))  # camera
    if f == 0:
        head(g, hx('6A4A2A'), 'short', look='down', mouth='o')
        arm(g, 'L', shirt, 'chest'); arm(g, 'R', shirt, 'chest')
        g.r(16, 25, 31, 31, hx('F2EAD0')); g.r(16, 25, 16, 31, hx('D8CBA8'))
        g.r(18, 27, 23, 27, hx('7FB0D8')); g.r(25, 28, 29, 28, hx('E07A5A')); g.r(20, 29, 27, 29, hx('9CC98A'))
    else:
        head(g, hx('6A4A2A'), 'short', look='up', mouth='o')
        arm(g, 'L', shirt, 'raise'); arm(g, 'R', shirt, 'raise')
        g.r(12, 3, 35, 7, hx('F2EAD0')); g.r(14, 4, 19, 4, hx('7FB0D8')); g.r(24, 5, 31, 5, hx('E07A5A'))
    g.r(15, 3, 32, 5, hat); g.r(13, 6, 34, 6, hat); g.r(15, 5, 32, 5, shade(hat))   # bucket hat
    return g

def flyer(f):
    g = Px()
    vest, tee, cap = hx('D8F03C'), hx('8C8C96'), hx('FF7A1A')
    legs(g, hx('3A3A48'), shoe=hx('F0F0F0'))
    torso(g, tee); g.r(16, 20, 21, 32, vest); g.r(26, 20, 31, 32, vest)
    g.r(16, 28, 21, 28, hx('B8B8B8')); g.r(26, 28, 31, 28, hx('B8B8B8'))   # reflective stripe
    head(g, hx('2D2340'), 'short', mouth='grin' if f else 'smile')
    g.r(17, 4, 30, 7, cap); g.r(17, 8, 33, 8, shade(cap))                 # cap w/ visor
    if f == 0:
        arm(g, 'L', tee, 'chest'); arm(g, 'R', tee, 'down')
        g.r(17, 23, 23, 30, WHITE); g.r(18, 24, 22, 25, hx('FF5A8A')); g.r(18, 27, 22, 27, hx('7FB0D8'))
    else:
        arm(g, 'L', tee, 'down'); arm(g, 'R', tee, 'out')
        g.r(19, 21, 30, 31, WHITE); g.r(20, 22, 29, 24, hx('FF5A8A'))
        g.r(20, 26, 27, 26, hx('7FB0D8')); g.r(20, 28, 25, 28, hx('7FB0D8')); g.r(26, 28, 29, 30, hx('FFD24A'))
    return g

def bujang(f):  # 부장님
    g = Px()
    suit, tie = hx('6B5A4A'), hx('8E2A3A')
    legs(g, shade(suit, .9), shoe=hx('3A2418'))
    torso(g, suit, wide=True)
    g.r(19, 19, 28, 33, WHITE); g.r(23, 20, 24, 30, tie); g.r(22, 19, 25, 20, tie)
    g.r(19, 30, 28, 33, WHITE); g.r(18, 31, 29, 33, WHITE)                  # belly pushing shirt out
    g.r(14, 32, 33, 33, hx('3A2418')); g.r(23, 32, 24, 33, hx('D8B040'))    # belt + buckle
    head(g, hx('3A3440'), 'bald', mouth='open' if f else 'flat')
    g.r(19, 11, 22, 14, None)
    for x0 in (18, 25):                                                     # glasses: light lens, thin frame
        g.r(x0, 10, x0+4, 14, hx('5A4A3A')); g.r(x0+1, 11, x0+3, 13, hx('D8EAF4'))
        g.r(x0+2, 12, x0+2, 13, EYE)
    g.r(23, 11, 24, 11, hx('5A4A3A'))
    g.r(21, 15, 26, 15, hx('3A3440'))                                       # moustache
    arm(g, 'L', suit, 'down')
    arm(g, 'R', suit, 'raise' if f else 'down')
    return g

def beggar(f):  # 앉아 있는 사람 - 존중하는 톤, 차분한 표정
    g = Px(); dy = 9
    coat, beanie, blanket = hx('6E7A5A'), hx('A04848'), hx('8A6E9E')
    # crossed legs + blanket on the floor
    g.r(10, 40, 37, 46, blanket); g.r(10, 40, 37, 40, shade(blanket, .9))
    for x in range(12, 37, 5): g.r(x, 42, x+1, 46, shade(blanket, .85))
    g.r(8, 45, 14, 46, SHOE); g.r(33, 45, 39, 46, SHOE)
    torso(g, coat, dy=dy-1)
    g.r(15, 20+dy, 32, 20+dy, shade(coat, .9)); g.r(23, 21+dy, 24, 31+dy, shade(coat, .75))   # zip
    head(g, hx('5A5060'), 'short', dy=dy, look='down', mouth='flat')
    g.r(19, 14+dy, 28, 18+dy, None)
    g.r(19, 17+dy, 28, 18+dy, hx('7A7080'))                                  # stubble
    g.r(16, 3+dy, 31, 8+dy, beanie); g.r(16, 8+dy, 31, 8+dy, shade(beanie)); g.r(23, 2+dy, 24, 2+dy, beanie)
    cup = hx('F2EAD0')
    if f == 0:
        arm(g, 'L', coat, 'chest', dy=dy-1); arm(g, 'R', coat, 'chest', dy=dy-1)
        g.r(21, 30, 26, 35, cup); g.r(21, 30, 26, 30, hx('C9B48A'))         # cup held at chest
    else:
        arm(g, 'L', coat, 'down', dy=dy-1); arm(g, 'R', coat, 'out', dy=dy-2)
        g.r(22, 31, 28, 37, cup); g.r(22, 31, 28, 31, hx('C9B48A')); g.r(24, 33, 25, 34, hx('D8B040'))
    return g

def staff(f):  # 역무원
    g = Px()
    uni, cap, band = hx('2E3F6E'), hx('243256'), hx('C8F04A')
    legs(g, shade(uni, .9), shoe=SHOE)
    torso(g, uni)
    g.r(20, 19, 27, 22, hx('E8EEF8')); g.r(23, 20, 24, 27, hx('B83A3A'))    # shirt + tie
    for y in (24, 28): g.r(17, y, 18, y, hx('D8B040')); g.r(29, y, 30, y, hx('D8B040'))
    g.r(27, 23, 30, 24, hx('D8B040'))                                       # name badge
    head(g, hx('2D2340'), 'short', mouth='open' if f else 'flat')
    g.r(16, 3, 31, 7, cap); g.r(15, 8, 32, 8, EYE); g.r(22, 4, 25, 6, hx('D8B040'))   # cap + emblem
    arm(g, 'L', uni, 'down'); g.r(12, 22, 14, 24, band)
    if f == 0:
        arm(g, 'R', uni, 'down')
    else:
        arm(g, 'R', uni, 'raise'); g.r(33, 16, 35, 18, band)
        g.r(24, 16, 28, 17, hx('C8CCD8')); g.r(27, 15, 29, 15, hx('C8CCD8'))   # whistle
    return g

def friend(f):  # 아는 친구
    g = Px()
    jacket, tee, cap = hx('5B7FB8'), hx('FFD24A'), hx('E0453A')
    legs(g, hx('2F3A52'), shoe=hx('F0F0F0'))
    g.r(15, 45, 22, 45, hx('E0453A')); g.r(25, 45, 32, 45, hx('E0453A'))
    torso(g, jacket); g.r(20, 19, 27, 32, tee); g.r(22, 23, 25, 26, hx('E0453A'))
    head(g, hx('2D2340'), 'short', mouth='grin' if f == 0 else 'open')
    blush(g)
    g.r(17, 4, 30, 7, cap); g.r(14, 6, 16, 7, shade(cap))                   # backwards cap
    arm(g, 'L', jacket, 'down')
    arm(g, 'R', jacket, 'wave', dy=0 if f == 0 else 0)
    if f == 1:   # waving hand moves
        g.r(34, 5, 40, 11, (0, 0, 0, 0)); g.r(38, 4, 42, 9, SKIN); g.r(36, 9, 38, 14, jacket)
    return g

def coworker(f):  # 아는 동료 (커피 두 잔)
    g = Px()
    card, blouse = hx('9C7BC9'), WHITE
    legs(g, hx('34344A'), shoe=SHOE)
    torso(g, blouse); g.r(15, 19, 18, 32, card); g.r(29, 19, 32, 32, card)
    g.r(20, 19, 20, 27, hx('3A6FD8')); g.r(27, 19, 27, 27, hx('3A6FD8')); g.r(21, 27, 26, 31, hx('3A6FD8'))
    g.r(22, 28, 25, 30, WHITE)                                              # ID card on lanyard
    head(g, hx('4A2E2A'), 'pony', mouth='smile' if f == 0 else 'open')
    blush(g)
    def cup(x, y):
        g.r(x, y, x+4, y+6, hx('A8693A')); g.r(x, y, x+4, y, WHITE); g.r(x+1, y-1, x+3, y-1, WHITE); g.r(x, y+3, x+4, y+3, WHITE)
    if f == 0:
        arm(g, 'L', card, 'chest'); arm(g, 'R', card, 'down'); cup(18, 22); cup(34, 30)
    else:
        arm(g, 'L', card, 'down'); arm(g, 'R', card, 'out'); cup(24, 22); cup(10, 30)
    return g

def commuter(kind):
    def make(f):
        g = Px(); bob = 1 if f == 1 else 0
        if kind == 1:   # 회사원 여성
            blazer = hx('34406B')
            legs(g, None, shoe=SHOE, skirt=hx('2A3354'))
            torso(g, blazer, dy=bob); g.r(21, 19+bob, 26, 25+bob, WHITE)
            head(g, hx('4A2E2A'), 'bob', dy=bob)
            arm(g, 'L', blazer, 'down', dy=bob); arm(g, 'R', blazer, 'down', dy=bob)
            g.r(34, 28+bob, 39, 34+bob, hx('8A3A4A')); g.r(35, 26+bob, 38, 27+bob, hx('8A3A4A'))
        elif kind == 2: # 대학생 후드 + 이어폰
            hood = hx('8A8FA0')
            legs(g, hx('3E5C8A'), shoe=hx('F0F0F0'))
            torso(g, hood, dy=bob); g.r(16, 19+bob, 31, 20+bob, shade(hood, .9))
            g.r(19, 27+bob, 28, 31+bob, shade(hood, .9))                    # pocket
            g.r(15, 20+bob, 16, 30+bob, hx('2D2340')); g.r(31, 20+bob, 32, 30+bob, hx('2D2340'))  # straps
            head(g, hx('2D2340'), 'side', dy=bob, look='down' if f else 'front')
            g.r(16, 13+bob, 16, 22+bob, WHITE); g.r(31, 13+bob, 31, 22+bob, WHITE)   # earphones
            arm(g, 'L', hood, 'down', dy=bob); arm(g, 'R', hood, 'down', dy=bob)
        elif kind == 3: # 등산복 아저씨
            jk = hx('E84A3A')
            legs(g, hx('B8A888'), shoe=hx('6A4A2A'))
            torso(g, jk, dy=bob); g.r(23, 19+bob, 24, 32+bob, hx('2D2340'))
            g.r(15, 24+bob, 32, 25+bob, hx('2D2340'))
            head(g, hx('9A9AA0'), 'short', dy=bob, mouth='frown')
            g.r(16, 4+bob, 31, 6+bob, hx('E8E0C8')); g.r(16, 7+bob, 34, 7+bob, hx('3A6A4A'))  # visor cap
            g.r(19, 11+bob, 28, 13+bob, EYE); g.r(20, 11+bob, 21, 11+bob, hx('5A8AB8'))      # sunglasses
            arm(g, 'L', jk, 'down', dy=bob); arm(g, 'R', jk, 'down', dy=bob)
        elif kind == 4: # 폰 보는 직장인
            suit = hx('4A4E58')
            legs(g, shade(suit, .9), shoe=SHOE)
            torso(g, suit, dy=bob); g.r(21, 19+bob, 26, 24+bob, WHITE); g.r(23, 20+bob, 24, 24+bob, hx('3A6FD8'))
            head(g, hx('2D2340'), 'side', dy=1, look='down', mouth='flat')
            arm(g, 'L', suit, 'chest', dy=bob); arm(g, 'R', suit, 'chest', dy=bob)
            g.r(20, 23+bob, 27, 28+bob, hx('1A1A22')); g.r(21, 24+bob, 26, 27+bob, hx('8FE3FF') if f == 0 else hx('B8F0FF'))
        elif kind == 5: # 할머니 + 장바구니 카트
            vest = hx('C0607A')
            legs(g, hx('6A4A8A'), shoe=hx('4A3A3A'))
            torso(g, hx('E8DCC8'), dy=bob); g.r(15, 19+bob, 19, 32+bob, vest); g.r(28, 19+bob, 32, 32+bob, vest)
            for y in (22, 27): g.p(16, y+bob, hx('FFD24A')); g.p(30, y+bob, hx('FFD24A'))
            head(g, hx('B9A8C9'), 'curly', dy=bob, mouth='smile')
            arm(g, 'L', vest, 'down', dy=bob); arm(g, 'R', vest, 'down', dy=bob)
            # cart (viewer right)
            g.r(36, 30, 45, 42, hx('3A6A9A')); g.r(36, 30, 45, 31, hx('2A4A7A'))
            for x in (38, 41, 44): g.r(x, 33, x, 41, hx('2A4A7A'))
            g.r(35, 24+bob, 36, 30, hx('8A8A90')); g.r(33, 24+bob, 36, 25+bob, hx('8A8A90'))
            g.r(37, 43, 39, 45, EYE); g.r(42, 43, 44, 45, EYE)
            g.r(37, 27, 41, 29, hx('5AB85A'))                                # 대파
        return g
    return make

ROSTER = [
    # key, maker, 이름
    ('npc_bujang_front',     bujang,      '부장님'),
    ('npc_staff_front',      staff,       '역무원'),
    ('npc_friend_front',     friend,      '아는 친구'),
    ('npc_coworker_front',   coworker,    '아는 동료'),
    ('npc_beggar_front',     beggar,      '도움을 청하는 사람'),
    ('npc_tourist_front',    tourist,     '길 묻는 관광객'),
    ('npc_flyer_front',      flyer,       '전단지 알바'),
    ('npc_commuter1_front',  commuter(1), '시민: 회사원'),
    ('npc_commuter2_front',  commuter(2), '시민: 대학생'),
    ('npc_commuter3_front',  commuter(3), '시민: 등산복 아저씨'),
    ('npc_commuter4_front',  commuter(4), '시민: 폰 보는 직장인'),
    ('npc_commuter5_front',  commuter(5), '시민: 장바구니 할머니'),
]

def build():
    manifest = {}
    for key, maker, _ in ROSTER:
        sheet = Image.new('RGBA', (G * S * 2, G * S), (0, 0, 0, 0))
        for f in range(2):
            fr = maker(f).im.resize((G * S, G * S), Image.NEAREST)
            sheet.paste(fr, (f * G * S, 0))
        sheet.save(os.path.join(OUT, key + '.png'))
        manifest[key] = {'file': f'npc/{key}.png', 'frame_w': 144, 'frame_h': 144, 'frames': 2}
    return manifest

if __name__ == '__main__':
    m = build()
    json.dump(m, open(os.path.join(OUT, 'manifest_npc.json'), 'w'), ensure_ascii=False, indent=2)
    print(len(m), 'sheets')
