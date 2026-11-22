"""F7 디버그: 평균 FPS를 콘솔(로그)에 남긴다. 화면에는 아무것도 그리지 않는다."""

import logging
import time

import config

_log = logging.getLogger(__name__)


class FpsMeter:
    """켜져 있는 동안 FPS_LOG_INTERVAL초마다 그동안의 평균 FPS를 로그로 남긴다."""

    def __init__(self) -> None:
        self.enabled = False
        self.last_average = 0.0  # 마지막으로 남긴 평균 FPS
        self._frames = 0
        self._since = time.perf_counter()

    def toggle(self) -> bool:
        """켜고 끈다. 켜진 상태면 True."""
        self.enabled = not self.enabled
        self.restart()
        _log.info("FPS 기록 %s", "켬" if self.enabled else "끔")
        return self.enabled

    def restart(self) -> None:
        """지금부터 다시 센다 (화면에 막 들어와 로딩 시간이 섞이지 않게)."""
        self._frames = 0
        self._since = time.perf_counter()

    def tick(self, strip_w: int) -> None:
        """한 프레임이 지났다. strip_w는 기록에 함께 남길 광선 띠 폭(px)."""
        if not self.enabled:
            return
        self._frames += 1
        elapsed = time.perf_counter() - self._since
        if elapsed < config.FPS_LOG_INTERVAL:
            return
        self.last_average = self._frames / elapsed
        _log.info("평균 FPS %.1f (광선 띠 폭 %dpx)", self.last_average, strip_w)
        self.restart()
