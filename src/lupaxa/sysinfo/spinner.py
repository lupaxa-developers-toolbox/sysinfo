"""Terminal progress spinner used while the CLI collects a report."""

from __future__ import annotations

import sys
import threading
import time
from typing import IO


class Spinner:
    """Animate a single-line progress indicator on a stream until stopped."""

    def __init__(
        self,
        message: str = "Collecting data — this may take a while...",
        stream: IO[str] | None = None,
        interval: float = 0.08,
    ) -> None:
        self.message = message
        self.stream = stream or sys.stderr
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        frames = "|/-\\"
        i = 0
        self.stream.write(self.message + " ")
        self.stream.flush()
        while not self._stop.is_set():
            self.stream.write("\r" + self.message + " " + frames[i % len(frames)])
            self.stream.flush()
            i += 1
            time.sleep(self.interval)
        self.stream.write("\r" + self.message + " ✓\n")
        self.stream.flush()

    def start(self) -> None:
        """Start animating on a background daemon thread."""
        self._thread.start()

    def stop(self) -> None:
        """Signal the animation to finish and wait briefly for the thread to exit."""
        self._stop.set()
        self._thread.join(timeout=1.5)
