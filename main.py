"""Application entry point."""

import logging
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QProcess, QTimer
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


class SourceCodeReloader:
    """Restart  after  files change during development."""

    def __init__(self, app, project_root):
        self.app = app
        self.project_root = project_root
        self.last_snapshot = self.snapshot()
        self.changed_at = None
        self.timer = QTimer(app)
        self.timer.setInterval(700)
        self.timer.timeout.connect(self.check_for_changes)
        self.timer.start()

    def snapshot(self):
        files = {}
        for path in self.project_root.rglob("*.py"):
            if any(part in {"__pycache__", ".venv", "venv", ".git", "build", "dist"} for part in path.parts):
                continue
            try:
                stat = path.stat()
                files[str(path)] = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue
        return files

    def check_for_changes(self):
        current = self.snapshot()
        if current != self.last_snapshot:
            self.last_snapshot = current
            self.changed_at = time.monotonic()
            return

        if self.changed_at is not None:
            if time.monotonic() - self.changed_at < 0.8:
                return
            self.restart()

    def restart(self):
        self.timer.stop()
        started, _process_id = QProcess.startDetached(
            sys.executable, sys.argv, str(self.project_root),
        )
        if started:
            self.app.quit()
        else:
            LOGGER.error("Could not restart the app after a source change")
            self.timer.start()
            self.changed_at = None


def main():
    log_path = Path(__file__).with_name("app.log")
    logging.basicConfig(filename=log_path, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("Project_worksummary")
    window = MainWindow()
    window.show()

    # Source runs get automatic UI refreshes; frozen/packaged builds do not.
    if not getattr(sys, "frozen", False):
        app.source_reloader = SourceCodeReloader(app, Path(__file__).resolve().parent)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
