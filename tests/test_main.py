import builtins
import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

import config
import main
import title_mode


@contextlib.contextmanager
def pico2d_import_fails(error):
    """`import pico2d` 한 줄만 주어진 예외로 실패하게 만든다."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pico2d":
            raise error
        return real_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", fake_import):
        yield


@contextlib.contextmanager
def fake_runtime():
    """창과 게임 루프 대신 호출 순서를 기록하는 가짜를 끼운다.

    실제 창이 뜨는 전체 흐름은 headless 스모크 테스트에서 확인한다.
    가짜 덕분에 순서가 잘못돼도 테스트가 진짜 게임 루프에 갇히지 않는다.
    """
    calls = mock.Mock()
    with (
        mock.patch("pico2d.open_canvas", calls.open_canvas),
        mock.patch("pico2d.hide_lattice", calls.hide_lattice),
        mock.patch("pico2d.close_canvas", calls.close_canvas),
        mock.patch("resource.preload_all", calls.preload_all),
        mock.patch("game_framework.run", calls.run),
    ):
        yield calls


def run_main():
    """main.main()을 실행해 (종료 코드, stderr에 찍힌 글)을 돌려준다."""
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code = main.main()
    return code, stderr.getvalue()


class Pico2dMissingTest(unittest.TestCase):
    def test_import_problems_exit_with_1_and_explain_how_to_install(self):
        errors = (
            ImportError("No module named 'pico2d'"),
            OSError("SDL2.dll 을 불러올 수 없습니다"),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                with pico2d_import_fails(error):
                    code, message = run_main()
                self.assertEqual(code, 1)
                self.assertIn(str(error), message)
                self.assertIn("pip install pico2d", message)
                self.assertIn("pip install pysdl2-dll", message)


class MissingFontTest(unittest.TestCase):
    def _assert_font_error(self, attribute):
        """config.<attribute>가 가리키는 폰트가 없을 때 이름을 알리고 창 없이 끝나는지."""
        original = getattr(config, attribute)
        with tempfile.TemporaryDirectory() as folder:
            missing = os.path.join(folder, os.path.basename(original))
            with (
                mock.patch.object(config, attribute, missing),
                fake_runtime() as calls,
            ):
                code, message = run_main()
        self.assertEqual(code, 1)
        self.assertIn("[리소스 오류]", message)
        self.assertIn(os.path.basename(original), message)
        self.assertEqual(calls.mock_calls, [])  # 창을 열기 전에 멈춘다

    def test_missing_regular_font_is_reported_by_file_name(self):
        self._assert_font_error("FONT_REGULAR")

    def test_missing_bold_font_is_reported_by_file_name(self):
        self._assert_font_error("FONT_BOLD")


class MissingResourceFolderTest(unittest.TestCase):
    def test_missing_resource_folder_lists_where_it_looked(self):
        # config는 import될 때 resource/ 를 찾는다. 다시 import하게 만들어 실패시킨다.
        with (
            mock.patch.dict(sys.modules),
            mock.patch("os.path.isfile", return_value=False),
            fake_runtime() as calls,
        ):
            del sys.modules["config"]
            code, message = run_main()
        self.assertEqual(code, 1)
        self.assertIn("[리소스 오류]", message)
        self.assertIn(config.ASSET_FOLDER_FALLBACK, message)
        self.assertEqual(calls.mock_calls, [])


class StartupTest(unittest.TestCase):
    def test_opens_the_canvas_preloads_runs_the_title_then_closes_the_canvas(self):
        with fake_runtime() as calls:
            code, message = run_main()
        self.assertEqual(code, 0)
        self.assertEqual(message, "")
        self.assertEqual(
            calls.mock_calls,
            [
                mock.call.open_canvas(config.SCREEN_W, config.SCREEN_H, True),
                mock.call.hide_lattice(),
                mock.call.preload_all(),
                mock.call.run(title_mode),
                mock.call.close_canvas(),
            ],
        )

    def test_canvas_is_closed_even_when_the_game_loop_raises(self):
        with fake_runtime() as calls:
            calls.run.side_effect = RuntimeError("boom")
            with self.assertRaises(RuntimeError):
                main.main()
        self.assertEqual(calls.mock_calls[-1], mock.call.close_canvas())


if __name__ == "__main__":
    unittest.main()
