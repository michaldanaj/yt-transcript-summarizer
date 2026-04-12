"""Główne okno aplikacji Transkrypcje YouTube."""

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .workers import SummaryWorker, TranscriptWorker


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Transkrypcje YouTube")
        self.setMinimumSize(900, 600)

        self.settings = QSettings("Transkrypcje", "TranskrypcjeYT")
        self.meta = None
        self.transcript_text = ""
        self.summary_text = ""
        self._worker = None

        self._build_ui()
        self._restore_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- URL input ---
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL filmu:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "https://www.youtube.com/watch?v=..."
        )
        self.url_input.returnPressed.connect(self._on_start)
        url_row.addWidget(self.url_input, 1)
        self.start_btn = QPushButton("Pobierz i streść")
        self.start_btn.clicked.connect(self._on_start)
        url_row.addWidget(self.start_btn)
        layout.addLayout(url_row)

        # --- Output directory ---
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Katalog wyjściowy:"))
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        dir_row.addWidget(self.dir_input, 1)
        dir_btn = QPushButton("Zmień...")
        dir_btn.clicked.connect(self._on_change_dir)
        dir_row.addWidget(dir_btn)
        layout.addLayout(dir_row)

        # --- API key ---
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("Gemini API Key:"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Klucz API Gemini")
        key_row.addWidget(self.key_input, 1)
        layout.addLayout(key_row)

        # --- Tabs ---
        self.tabs = QTabWidget()
        self.transcript_view = QTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setFontFamily("monospace")
        self.tabs.addTab(self.transcript_view, "Transkrypcja")

        self.summary_view = QTextEdit()
        self.summary_view.setReadOnly(True)
        self.tabs.addTab(self.summary_view, "Streszczenie")

        layout.addWidget(self.tabs, 1)

        # --- Status bar ---
        status_row = QHBoxLayout()
        self.status_label = QLabel("Gotowe")
        status_row.addWidget(self.status_label, 1)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.hide()
        status_row.addWidget(self.progress)
        layout.addLayout(status_row)

    def _restore_settings(self) -> None:
        output_dir = self.settings.value(
            "output_dir", str(Path.home() / "Dokumenty")
        )
        self.dir_input.setText(output_dir)

        api_key = self.settings.value("api_key", "")
        if not api_key:
            api_key = (
                os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
                or ""
            )
        self.key_input.setText(api_key)

        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def _save_settings(self) -> None:
        self.settings.setValue("output_dir", self.dir_input.text())
        self.settings.setValue("api_key", self.key_input.text())
        self.settings.setValue("geometry", self.saveGeometry())

    def closeEvent(self, event) -> None:
        self._save_settings()
        super().closeEvent(event)

    def _on_change_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Wybierz katalog wyjściowy", self.dir_input.text()
        )
        if path:
            self.dir_input.setText(path)
            self._save_settings()

    def _set_busy(self, busy: bool) -> None:
        self.start_btn.setEnabled(not busy)
        self.url_input.setEnabled(not busy)
        if busy:
            self.progress.show()
        else:
            self.progress.hide()

    def _on_start(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            return

        api_key = self.key_input.text().strip()
        if not api_key:
            QMessageBox.warning(
                self,
                "Brak klucza API",
                "Podaj klucz Gemini API Key.",
            )
            self.key_input.setFocus()
            return

        self.transcript_view.clear()
        self.summary_view.clear()
        self.meta = None
        self.transcript_text = ""
        self.summary_text = ""
        self._set_busy(True)

        self._worker = TranscriptWorker(url)
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_transcript_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_status(self, msg: str) -> None:
        self.status_label.setText(msg)

    def _on_transcript_done(self, text: str, meta) -> None:
        self.meta = meta
        self.transcript_text = text
        self.transcript_view.setPlainText(text)
        self.tabs.setCurrentIndex(0)

        # Zapisz transkrypcję
        self._save_transcript()

        # Teraz generuj streszczenie
        api_key = self.key_input.text().strip()
        self._worker = SummaryWorker(text, api_key, self.meta)
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_summary_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_summary_done(self, summary: str) -> None:
        self.summary_text = summary
        self.summary_view.setMarkdown(summary)
        self.tabs.setCurrentIndex(1)
        self._set_busy(False)

        # Zapisz streszczenie i otwórz w Typie
        summary_path = self._save_summary()
        if summary_path:
            self._open_in_typora(summary_path)

        self.status_label.setText("Gotowe — pliki zapisane")

    def _on_error(self, msg: str) -> None:
        self._set_busy(False)
        self.status_label.setText(f"Błąd: {msg}")
        QMessageBox.critical(self, "Błąd", msg)

    def _output_dir(self) -> Path:
        return Path(self.dir_input.text())

    def _save_transcript(self) -> Path | None:
        if not self.meta or not self.transcript_text:
            return None
        path = self._output_dir() / self.meta.safe_filename("_transcript.txt")
        path.write_text(self.transcript_text, encoding="utf-8")
        return path

    def _save_summary(self) -> Path | None:
        if not self.meta or not self.summary_text:
            return None
        path = self._output_dir() / self.meta.safe_filename(".md")
        path.write_text(self.summary_text, encoding="utf-8")
        return path

    def _open_in_typora(self, path: Path) -> None:
        try:
            subprocess.Popen(["typora", str(path)])
        except FileNotFoundError:
            # Typora niedostępna — otwórz domyślną aplikacją
            subprocess.Popen(["xdg-open", str(path)])


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Transkrypcje YouTube")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
