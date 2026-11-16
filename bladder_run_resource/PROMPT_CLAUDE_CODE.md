# BLADDER RUN — 2차 발표용 데모 빌드 (로드맵 1~2주차: 핵심 루프 완성)

너는 Python 3 + **pico2d**로 2D 횡스크롤 캐주얼 액션 게임 **BLADDER RUN**을 만드는 개발자야.
지금 폴더에는 `resource/`(이미지·사운드·폰트)만 있고 코드는 아직 없다. 아래 명세대로 코드를 처음부터 작성해줘.
이 코드는 일회용 데모가 아니라 3~4주차에도 계속 이어서 개발할 **실제 코드베이스**다. 그러니 구조를 깔끔하게 잡고, 모든 수치는 한 곳(config.py)에 모아줘.

---

## 0. 게임 한 줄 요약
출근길 지하철에서 내린 회사원 **김급해**가 **참을성 게이지가 100%가 되기 전에 역 화장실(WC)까지 도착**해야 하는 게임이다.
핵심 재미는 **"빨리 갈까(달리기), 안전하게 갈까(걷기)"**의 선택이다. 달리면 빠르지만 게이지가 더 빨리 오르고, 부딪히면 넘어진다.

## 1. 이번 빌드 범위 (중요)
기획서 로드맵의 **1주차 + 2주차 = "핵심 루프 완성"**까지만 만든다.

**만들 것**
- 1주차: 프로젝트 구조, 장면(모드) 전환, 이동·달리기·점프와 애니메이션, 게이지 상승과 단계 판정, 캐릭터 스프라이트 적용
- 2주차: 장애물 4종, 아이템 3종, 충돌 판정(사각형 겹침)과 효과, 횡스크롤 카메라
- 루프를 돌리기 위한 최소한의 장치:
  - 게이지·거리 HUD
  - 성공/실패 판정과 단순한 결과 화면
  - 재시작
  - 최소 타이틀
  - 효과음/BGM 연결 (리소스가 이미 있으므로 포함)

**만들지 말 것 (3~4주차 범위)**
- 스테이지 선택 화면, 스테이지 1·3 데이터, 스테이지 3 "청소 중" 반전
- 화면 흔들림, 95%의 붉은 테두리, 연출 다듬기, 최고 기록·랭킹
- 이 항목들은 나중에 쉽게 붙일 수 있게 **구조(훅)만** 열어두고 구현하지 마.

## 2. 환경
- Python 3.10+, `pip install pico2d`. Windows라면 SDL2 DLL이 필요할 수 있으니 실행 에러가 나면 `pip install pysdl2-dll`을 안내해줘.
- 해상도는 **1280×720**이다. pico2d 좌표계는 **원점이 왼쪽 아래**이고 `draw(x, y)`는 이미지 **중심** 기준이다.
- 폰트: `resource/font/Galmuri11.ttf`, `resource/font/Galmuri11-Bold.ttf` (사용자가 직접 넣어둠). 파일이 없으면 어떤 파일이 필요한지 알려주는 명확한 에러 메시지를 띄워줘.
- 작업 순서대로 **git 커밋**을 남겨줘(.gitignore에 `__pycache__/` 포함). 기획서에 "매주 Git에 커밋해 진행 상황 기록"이라고 되어 있다.

## 3. 리소스 (수정 금지, 그대로 사용)
- `resource/image/manifest.json`에 모든 시트의 `file`, `frame_w`, `frame_h`, `frames`(플레이어는 `fps` 포함)가 있다. **이 파일을 읽어서 로드해.** 경로나 프레임 수를 하드코딩하지 마.
- 모든 스프라이트 시트는 **가로 한 줄**이다.
  - 프레임 i는 `image.clip_draw(i*fw, 0, fw, fh, x, y)`로 그린다.
  - 좌우 반전은 `image.clip_composite_draw(i*fw, 0, fw, fh, 0, 'h', x, y, fw, fh)`로 한다.
- 이미지는 이미 픽셀 3배(배경 포함)로 확대되어 있다. **런타임에 크기를 바꾸지 말고 원본 크기 그대로** 그려야 픽셀이 뭉개지지 않는다.
- 같은 이미지를 여러 번 `load_image` 하지 말고 리소스 캐시(모듈 또는 클래스 변수)로 한 번만 로드해.

| 그룹 | 시트 | 비고 |
|---|---|---|
| player | `player_{mood}_{anim}` | mood: `calm`(0–49%) / `sweat`(50–79%) / `strain`(80–94%) / `limit`(95–99%)<br>anim: `idle`(2f) `walk`(4f) `run`(4f) `jump`(2f: 0=상승, 1=하강) `fall`(2f, 넘어짐) `waddle`(4f, 엉거주춤)<br>144×144, **오른쪽**을 봄. 발바닥이 이미지 하단에서 **3px 위**에 있다. |
| npc | `npc_tourist`, `npc_flyer`, `npc_boss`(f1=손 들고 부르는 동작), `npc_commuter1~3` | 144×144, 2f, **왼쪽**을 봄. 발 위치 규칙은 플레이어와 같다. |
| item | `item_breath`(2f), `item_gum`(2f), `item_shortcut`(1f, 지름길 표지판) | |
| fx | `fx_exclaim`(상사 "!", 2f 깜빡임), `fx_question`(관광객 "?"), `fx_speech`(빈 말풍선, 안에 폰트로 대사), `fx_stars`(3f, 기절 별), `fx_dust`(3f, 달리기 먼지), `fx_paper`(전단지가 몸에 붙음) | |
| ui | `ui_gauge_frame`(336×36), `ui_gauge_fill_{blue,yellow,orange,red}`(324×24), `ui_progress_frame`, `ui_progress_fill`, `ui_wc_badge`, `ui_head_icon`, `title_logo` | 채움 바는 `clip_draw`로 **왼쪽부터 퍼센트만큼 잘라서** 그린다. |
| prop | `prop_train`(시작 지점 지하철), `prop_gate`(개찰구), `prop_wc_door`(f0 닫힘 / f1 열림=성공), `prop_sign_wc`, `prop_stairs_sign` | 장식 + 골인 지점 |
| bg | `bg_far`(1344×720, 불투명), `bg_mid`(1344×720, 투명: 기둥·벤치), `floor_tile`(192×120), `floor_stairs`(96×120, 계단 구간 바닥) | 가로로 이어붙이면 끊김 없이 반복된다. |
| sound | `resource/sound/*.wav` | 아래 7절 참고 |

- **바닥(ground) y = 120**: 바닥 타일 높이가 120이고, 캐릭터 발이 이 높이에 닿는다.
- 캐릭터·NPC를 그리는 y는 `ground_y + frame_h/2 - 3`이다.

## 4. 코드 구조 (수업에서 쓰는 pico2d 패턴을 따름)
```
main.py              # open_canvas(1280,720) → game_framework.run(title_mode) → close_canvas
game_framework.py    # 모드 스택: run, change_mode, push_mode, pop_mode, quit, frame_time
game_world.py        # 레이어별 객체 리스트, add/remove_object, update, render,
                     # add_collision_pair / handle_collisions (get_bb 기반)
config.py            # ★ 모든 밸런스 수치 (아래 5절)
resource.py          # manifest 로드, 이미지·사운드 캐시, Sprite 헬퍼(frame, fps, draw, flip)
state_machine.py     # 이벤트 기반 상태 머신 (수업 방식: (조건함수 → 다음 상태) 전이표)
camera.py            # cam_x = player.x - W//3, clamp(0, cam_x, stage.length - W)
background.py        # bg_far(패럴랙스 0.3), bg_mid(0.6), 바닥 타일(1.0, 계단 구간은 floor_stairs)
player.py            # 상태: Idle, Walk, Run, Jump, Stunned(넘어짐/정지/대화 공용)
gauge.py             # 게이지 값, 단계(stage 0~4) 판정, 단계 변화 콜백(사운드·외형 전환)
obstacle.py          # Obstacle 기반 클래스 + Tourist, Flyer, Boss, Crowd
item.py              # Item 기반 클래스 + Breath, Gum, Shortcut
stage_data.py        # 스테이지 배치 데이터 (dict/list, 코드와 분리)
stage.py             # 데이터를 읽어 객체 생성, length, goal_x, 계단 구간 정보
hud.py               # 게이지 바, %, "WC까지 n m" 진행 바, STAGE 표시
fx.py                # 잠깐 떴다 사라지는 이펙트 객체 (별, 먼지, 느낌표 등)
sound.py             # BGM/SFX 래퍼 (게이지 단계에 따라 BGM 전환)
title_mode.py / play_mode.py / result_mode.py
```
- 모든 게임 객체는 `update()`, `draw()`, `get_bb()`, `handle_collision(group, other)`를 가진다.
- PlayMode는 game_world를 한 번에 순회한다.
- 화면에 그릴 때는 `screen_x = world_x - camera.x`를 쓴다.

## 5. 규칙과 수치 (config.py에 상수로 모아두기)
**속도**
- 걷기 200 px/s, 달리기 400 px/s (SHIFT를 누르는 동안).
- 속도 배율은 곱해서 적용한다:
  - 게이지 50% 이상이면 ×0.9
  - 계단 구간이면 ×0.7
  - 전단지에 붙잡혔으면 3초간 ×0.5
- 점프: 초기 속도 880 px/s, 중력 2000 px/s². 발 기준 최고 높이는 약 190px이다.
  - 관광객·전단지·상사(BB 높이 100)는 걸으면서도 넘을 수 있어야 하고, 인파(BB 높이 220)는 못 넘어야 한다.
  - 공중에서도 좌우 이동은 된다.

**게이지** (기획서 공식 그대로)
```
gauge += BASE_RATE[stage] * (1.6 if running else 1.0) * frame_time   # 단위 %/s
BASE_RATE = {1: 1.0, 2: 1.4, 3: 1.6}   # 이번 빌드는 stage 2만 사용
```
- 껌 효과가 켜져 있는 동안에는 게이지 상승이 멈춘다.
- 0~100으로 clamp한다.

| 단계 | 범위 | 효과 | 스프라이트 mood |
|---|---|---|---|
| 평온 | 0–49% | 정상 조작 | calm |
| 식은땀 | 50–79% | 땀 이펙트, 이동 속도 −10%, 진입 시 "꾸르륵"(sfx_growl) | sweat |
| 엉거주춤 | 80–94% | **달리기 불가**(SHIFT 무시), 걷기 대신 `waddle` 애니, BGM → bgm_tense | strain |
| 한계 | 95–99% | **←→ 입력 반전**, 심장 박동 루프(sfx_heartbeat) | limit |
| GAME OVER | 100% | 실패 → 결과 화면 "…늦었다" | — |

**달리다 부딪히면**
- 장애물 효과에 더해 **넘어짐**(fall 애니 + fx_stars, 1초 정지, 게이지 +10%)이 추가된다.
- 정지 시간이 장애물 정지 시간과 겹치면 긴 쪽을 쓴다.
- 걷다가 부딪히면 넘어지지 않는다.

**장애물** (충돌 후에는 그 장애물을 비활성화해서 중복으로 맞지 않게 한다. 인파는 예외)

| 장애물 | 효과 | 피하는 법 | 연출 |
|---|---|---|---|
| OBS-1 길 묻는 관광객 `npc_tourist` | 닿으면 2초 정지 | 점프로 넘기 | 머리 위 fx_question. 충돌 후 지도 보며 퇴장 또는 페이드 |
| OBS-2 전단지 알바 `npc_flyer` | 닿으면 3초간 이동 속도 −50% | 점프로 넘기 | 효과 중 몸에 fx_paper |
| OBS-3 직장 상사 `npc_boss` | 대화 시작 → 1.5초 정지 + 게이지 +15% (말풍선 "김대리~ 잠깐만!" + sfx_boss_talk) | "!"를 보고 타이밍 맞춰 점프 | 아래 참고 |
| OBS-4 계단·인파 `npc_commuter1~3` 묶음 | 닿으면 뒤로 120px 밀림 (sfx_push) | 틈이 열릴 때 통과 | 아래 참고 |

- **직장 상사 등장 방식**
  - 플레이어가 상사 x − 600까지 오면 화면 오른쪽 끝(상사 머리 위 높이)에 **fx_exclaim이 0.5초** 깜빡이고 sfx_warning이 울린다.
  - 그다음 상사가 160 px/s로 플레이어 쪽(왼쪽)으로 걸어오며 f1(손 드는 동작)을 보여준다.
  - 대화가 끝나면 오른쪽으로 퇴장한다.
- **계단과 인파**
  - **계단 구간**은 바닥을 floor_stairs로 그리고 그 구간에서 속도 ×0.7을 적용한다.
  - **인파**는 3~4명이 한 묶음이고, 너무 높아서 점프로 넘을 수 없다(BB 높이 약 220).
  - 2.5초 주기로 1.0초 동안 **"틈"**이 열린다. 이때 가운데 사람들이 위아래로 벌어지며 뒤로 물러나는 연출을 하고, 충돌 박스를 끈다.

**아이템** (닿으면 획득하고 제거. 위아래로 살짝 둥둥 뜨는 연출)
- 심호흡 `item_breath`: 게이지 −15% (sfx_item_breath)
- 껌 `item_gum`: 3초간 게이지 상승 정지. HUD 게이지 옆에 남은 시간 표시 (sfx_item_gum)
- 지름길 `item_shortcut`: 앞으로 800px 순간이동. 먼지 이펙트를 내고 카메라가 따라간다 (sfx_item_shortcut)
- 배치 원칙: 장애물 바로 뒤나 점프해야 닿는 높이에 둔다. 먹으러 갈지 말지가 하나의 선택이 되게 한다.

**충돌 박스 권장값** (발 기준 x, y)
- 플레이어: x±20, 발 ~ 발+125
- NPC: x±22, 발 ~ 발+100 (모자나 손 같은 머리 위 장식은 판정에서 뺌)
- 인파 묶음: 멤버 전체 폭, 높이 220
- 아이템: 이미지 크기의 80%

## 6. 데모 스테이지 = Stage 2 "출근 러시아워" (stage_data.py)
기획서 Stage 2의 수치를 그대로 쓴다: 길이 9,000px, 상승률 1.4%/s, 장애물 4종 전부, 인파 밀집, 아이템은 심호흡 2·껌 1·지름길 1.
배치(x는 월드 좌표, item의 h는 바닥에서의 높이)는 아래와 같다.

```
length = 9000, goal_x = 8800, player_start_x = 150
deco:  prop_train x=500 | prop_gate x=2450, 2550, 2650 | prop_stairs_sign x=4150 (벽 높이)
       prop_sign_wc 몇 개를 벽 높이에 띄엄띄엄 | prop_wc_door x=8800 (골인)
stairs zone: 4200 ~ 5400
obstacles: tourist 1000 | flyer 1800 | boss 3300 | crowd(4명) 4700 | tourist 5900
           flyer 7000 | crowd(3명) 7600
items: breath 1150 (h=150, 점프 필요) | gum 3550 (h=40) | breath 6050 (h=150)
       shortcut 6500 (h=0, 표지판)
```
- 플레이어가 `goal_x`에 닿으면 WC 문이 f1(열림)로 바뀌고 sfx_clear가 울린다. 약 1.5초 뒤 결과 화면(CLEAR)으로 넘어간다.
- 걷기만 하면 약 45초에 게이지 63% 정도가 되어야 한다(기획서 표 기준). 수치를 조정하면 config.py에서만 바꿔.

## 7. 사운드 연결 (`resource/sound/`)
- BGM은 `load_music`으로 불러 `repeat_play()`로 튼다.
  - `bgm_normal`(평상시)과 `bgm_tense`(게이지 80% 이상)가 있고, 단계가 바뀔 때 전환한다.
  - 성공·실패 시 BGM을 멈춘다.
- SFX는 `load_wav`로 불러 `play()`로 튼다. 볼륨은 sound.py에서 한 번에 조절할 수 있게 해줘.

| 파일 | 상황 |
|---|---|
| `sfx_jump` | 점프 |
| `sfx_bump` | 장애물 충돌 |
| `sfx_fall` | 넘어짐 |
| `sfx_push` | 인파에 밀림 |
| `sfx_item_breath` / `sfx_item_gum` / `sfx_item_shortcut` | 아이템 획득 |
| `sfx_warning` | 상사 "!" |
| `sfx_boss_talk` | 상사 대화 |
| `sfx_growl` | 50% 진입 시 1회, 이후 50% 이상 구간에서 8~12초마다 랜덤으로 |
| `sfx_heartbeat` | 95% 이상에서 1초 루프. 95% 미만으로 내려가면 정지 |
| `sfx_clear` | 성공 (천사 합창) |
| `sfx_fail` | 실패 (그 뒤는 정적) |

## 8. 화면 구성
**HUD** (기획서 '플레이 화면 구성' 그대로)
- 왼쪽 위
  - 게이지 프레임과 채움 바를 그린다. 채움 바는 프레임 안쪽으로 상하좌우 6px 들어간 위치에서 시작한다. 채움 색은 단계에 따라 바뀐다: blue(0–49) / yellow(50–79) / orange(80–94) / red(95+).
  - 아래에 `72%` 같은 퍼센트를 Galmuri로 쓴다. 글자 색은 채움 색과 맞춘다.
  - 껌 효과 중이면 옆에 남은 시간을 표시한다.
- 위쪽 가운데
  - 형식은 `WC까지 124m`로 한다. 남은 거리는 (goal_x − x) / 60을 반올림한 값이다.
  - 그 아래에 진행 바를 두고, 진행률 위치에 ui_head_icon을, 오른쪽 끝에 ui_wc_badge를 놓는다.
- 오른쪽 위: `STAGE 2`를 노란색으로 쓴다.

**TitleMode (최소)**
- 남색 배경(#1D1B3A), 가운데에 title_logo를 둔다.
- 오른쪽에 player_strain_waddle을 2배 크기로 애니메이션한다. 타이틀만 예외로 2배 확대해도 된다.
- 아래에 "SPACE 키로 시작"을 깜빡이게 쓴다.
- SPACE를 누르면 PlayMode로, ESC를 누르면 종료한다.

**ResultMode (최소)**
- CLEAR: 노란 배경에 "CLEAR! 무사 도착"과 걸린 시간·최종 게이지를 보여준다.
- FAIL: 검은 화면에 "…늦었다" 한 줄만 보여준다.
- 두 경우 모두 "SPACE 다시하기 / ESC 타이틀"을 표시한다. 재시작은 즉시 된다.

**PlayMode 키**
- ←→ 이동, SHIFT 달리기(누르는 동안), SPACE 점프, ESC 타이틀
- 플레이어는 왼쪽으로도 갈 수 있다. 왼쪽으로 가면 스프라이트를 좌우 반전한다.
- **개발용 디버그 키**: F1/F2/F3/F4 → 게이지를 0/50/80/95로 설정, B → 충돌 박스 표시, G → 게이지 고정
  - 화면에는 아무 표시도 하지 마. 녹화 화면에 나오면 안 된다.
  - 단, B를 켰을 때만 `draw_rectangle`로 충돌 박스를 그린다.

## 9. 작업 순서 (단계마다 실행해서 확인하고 커밋)
1. 프레임워크(main, game_framework, game_world, resource, config)와 Title → Play 전환, 배경 패럴랙스와 바닥 → `커밋: 프로젝트 구조, 장면 전환`
2. Player 상태 머신(Idle/Walk/Run/Jump)과 애니메이션, 카메라 → `커밋: 이동·달리기·점프`
3. Gauge, 단계별 mood 스프라이트 전환, 80%/95% 규칙, 100% 실패 → `커밋: 게이지 상승과 단계 판정` (← 1주차 완료)
4. stage_data와 장애물 4종, 충돌, Stunned 상태, 넘어짐 → `커밋: 장애물 4종 + 충돌`
5. 아이템 3종, 골인, ResultMode → `커밋: 아이템 3종 + 성공/실패`
6. HUD, 사운드, 이펙트 → `커밋: HUD·사운드 연결 (핵심 루프 완성)` (← 2주차 완료)

각 단계가 끝나면 무엇을 바꿨는지, 어떻게 확인했는지 짧게 보고해줘.

## 10. 완료 기준 체크리스트
- [ ] `python main.py` 실행 → 타이틀 → SPACE → 플레이 → 성공/실패 → 다시하기까지 에러 없이 돈다.
- [ ] 걷기 / 달리기 / 점프 / 엉거주춤 / 넘어짐 애니메이션이 상황에 맞게 나온다.
- [ ] 게이지가 50/80/95%에서 외형·조작·사운드가 바뀌고, 100%면 "…늦었다"가 뜬다.
- [ ] 장애물 4종과 아이템 3종이 명세대로 동작한다. 달리다 부딪히면 넘어진다.
- [ ] 카메라가 부드럽게 따라가고, 스테이지 양 끝에서 멈춘다.
- [ ] 모든 밸런스 수치는 config.py에만 있다.
- [ ] 픽셀 이미지가 확대되거나 흐려지지 않는다.
- [ ] frame_time 기반이라 프레임 속도와 무관하게 같은 속도로 움직인다.

## 11. 하지 말 것
- `resource/` 안의 파일을 수정·삭제·재생성하지 마. 필요한 그림이 없으면 `draw_rectangle` 같은 임시 표시로 대신하고, **무엇이 더 필요한지 나에게 보고**해.
- 1절의 "만들지 말 것" 항목은 구현하지 마.
- 외부 라이브러리를 추가하지 마 (pico2d + 표준 라이브러리만 사용).
