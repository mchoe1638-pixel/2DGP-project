"""소리: 효과음(SFX)과 배경음(BGM)을 한곳에서 틀고 멈춘다.

- init()을 부르기 전에는 꺼져 있다. 창을 열기 전이나 테스트에서는 어떤 호출도 아무 일도 하지 않는다.
- 소리 파일은 init()에서 한꺼번에 불러 둔다. 장치나 파일이 없으면 그 소리만 건너뛰고 게임은 이어진다.
- 볼륨은 set_volume() 하나로 효과음과 배경음을 함께 조절한다.
- pico2d의 Wav에는 멈추는 기능이 없다. 심장박동은 1초짜리 소리를 1초마다 다시 틀어 이어 붙이고,
  조건이 풀리면 다시 틀지 않는 것으로 멈춘다 (마지막 한 번은 끝까지 울린다).
"""

import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import config
from util import clamp

if TYPE_CHECKING:
    from pico2d import Music, Wav

# 효과음 (소리 폴더의 파일 이름에서 .wav를 뗀 것)
JUMP = "sfx_jump"
BUMP = "sfx_bump"
FALL = "sfx_fall"
PUSH = "sfx_push"
ITEM_BREATH = "sfx_item_breath"
ITEM_GUM = "sfx_item_gum"
ITEM_SHORTCUT = "sfx_item_shortcut"
WARNING = "sfx_warning"
BOSS_TALK = "sfx_boss_talk"
GROWL = "sfx_growl"
HEARTBEAT = "sfx_heartbeat"
CLEAR = "sfx_clear"
FAIL = "sfx_fail"
# 배경음
BGM_NORMAL = "bgm_normal"
BGM_TENSE = "bgm_tense"

EFFECT_NAMES = (
    JUMP,
    BUMP,
    FALL,
    PUSH,
    ITEM_BREATH,
    ITEM_GUM,
    ITEM_SHORTCUT,
    WARNING,
    BOSS_TALK,
    GROWL,
    HEARTBEAT,
    CLEAR,
    FAIL,
)
MUSIC_NAMES = (BGM_NORMAL, BGM_TENSE)
MAX_MIXER_VOLUME = 128  # SDL_mixer의 가장 큰 볼륨. pico2d의 set_volume은 0~128을 받는다

_log = logging.getLogger(__name__)
_effects: dict[str, "Wav"] = {}
_music: dict[str, "Music"] = {}
_current_bgm: str | None = None  # 지금 나오는 배경음 이름
_heartbeat_left = 0.0  # 다음 심장박동까지 남은 시간(초)


# ---------------------------------------------------------------- 준비
def _load(loader: Callable[[str], Any], name: str) -> Any:
    """소리 폴더의 name.wav를 loader로 불러온다. 장치나 파일이 없어 못 불러오면 None."""
    try:
        return loader(os.path.join(config.SOUND_DIR, f"{name}.wav"))
    except OSError:  # pico2d는 못 불러오면 IOError(= OSError)를 던진다
        return None


def _load_group(
    names: tuple[str, ...], loader: Callable[[str], Any], store: dict[str, Any]
) -> list[str]:
    """names를 모두 불러 store에 담고, 못 불러온 이름들을 돌려준다."""
    store.clear()
    for name in names:
        loaded = _load(loader, name)
        if loaded is not None:
            store[name] = loaded
    return [name for name in names if name not in store]


def init(volume: float = config.SOUND_VOLUME) -> None:
    """소리 파일을 불러 두고 소리를 켠다. pico2d 창(오디오 장치)을 연 뒤에 한 번 부른다."""
    import pico2d  # 지연 import: 창 없이 이 모듈을 import하는 테스트를 위해

    # 오디오 장치를 못 열었으면 파일마다 같은 오류가 반복되니, 먼저 한 번만 알리고 끈다
    if not pico2d.pico2d.audio_on:
        _log.warning("오디오 장치를 쓸 수 없어 소리 없이 진행합니다.")
        return
    missing = _load_group(EFFECT_NAMES, pico2d.load_wav, _effects)
    missing += _load_group(MUSIC_NAMES, pico2d.load_music, _music)
    if missing:
        _log.warning("불러오지 못한 소리는 건너뜁니다: %s", ", ".join(missing))
    set_volume(volume)


def _mixer_level(level: float) -> int:
    return round(level * MAX_MIXER_VOLUME)


def set_volume(volume: float) -> None:
    """효과음과 배경음의 볼륨을 한꺼번에 정한다 (0.0 ~ 1.0). 배경음은 BGM_VOLUME_RATIO만큼 낮다."""
    volume = clamp(0.0, volume, 1.0)
    for wav in _effects.values():
        wav.set_volume(_mixer_level(volume))
    for music in _music.values():
        music.set_volume(_mixer_level(volume * config.BGM_VOLUME_RATIO))


# ---------------------------------------------------------------- 틀기
def play_sfx(name: str) -> None:
    """효과음을 한 번 튼다. 꺼져 있거나 불러오지 못한 소리면 아무 일도 하지 않는다."""
    wav = _effects.get(name)
    if wav is not None:
        wav.play()


def play_bgm(name: str) -> None:
    """배경음을 처음부터 되풀이해 튼다. 이미 그 곡이 나오는 중이면 그대로 둔다."""
    global _current_bgm
    music = _music.get(name)
    if music is None or name == _current_bgm:
        return
    music.repeat_play()
    _current_bgm = name


def stop_bgm() -> None:
    """나오던 배경음을 멈춘다. 효과음은 끝까지 울린다."""
    global _current_bgm
    music = _music.get(_current_bgm) if _current_bgm is not None else None
    if music is not None:
        music.stop()
    _current_bgm = None


def stop_effects() -> None:
    """울리는 중인 효과음을 모두 멈춘다 (배경음은 그대로). 소리가 꺼져 있으면 아무 일도 하지 않는다."""
    if not _effects:
        return
    import pico2d  # 지연 import: 창 없이 이 모듈을 import하는 테스트를 위해

    pico2d.Mix_HaltChannel(-1)  # -1: 모든 효과음 채널 (배경음은 채널을 쓰지 않는다)


def update_heartbeat(dt: float, active: bool) -> None:
    """active인 동안 심장박동 소리를 HEARTBEAT_PERIOD마다 다시 틀어 끊김 없이 이어 붙인다."""
    global _heartbeat_left
    if not active:
        stop_heartbeat()
        return
    _heartbeat_left -= dt
    if _heartbeat_left <= 0.0:
        play_sfx(HEARTBEAT)
        _heartbeat_left += config.HEARTBEAT_PERIOD


def stop_heartbeat() -> None:
    """심장박동을 더 이어 붙이지 않는다 (이미 울리는 한 번은 끝까지 울린다). 다음엔 곧바로 다시 울린다."""
    global _heartbeat_left
    _heartbeat_left = 0.0
