"""BLADDER RUN 실행 진입점: python main.py"""

import sys

PICO2D_HELP = (
    "pico2d 를 불러오지 못했습니다: {error}\n"
    "  - 설치: pip install pico2d\n"
    "  - Windows 에서 DLL 오류가 나면: pip install pysdl2-dll"
)


def main() -> int:
    try:
        import pico2d
    except (ImportError, OSError) as error:
        print(PICO2D_HELP.format(error=error), file=sys.stderr)
        return 1

    try:
        import config
        import resource

        resource.require_font_file(config.FONT_REGULAR)
        resource.require_font_file(config.FONT_BOLD)
    except FileNotFoundError as error:
        print(f"[리소스 오류] {error}", file=sys.stderr)
        return 1

    import game_framework
    import sound
    import title_mode

    pico2d.open_canvas(config.SCREEN_W, config.SCREEN_H, True)
    pico2d.hide_lattice()
    try:
        resource.preload_all()
        sound.init()
        game_framework.run(title_mode)
    finally:
        pico2d.close_canvas()
    return 0


if __name__ == "__main__":
    sys.exit(main())
