"""Główne okno aplikacji Transkrypcje YouTube."""

import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
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

from ..summarizer import Provider, postprocess_summary
from .workers import SummaryWorker, TranscriptWorker


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        try:
            version = importlib.metadata.version("transkrypcje")
        except importlib.metadata.PackageNotFoundError:
            version = "dev"
        self.setWindowTitle(f"Transkrypcje YouTube v{version}")
        icon_path = Path.home() / ".local/share/icons/transkrypcje-gui.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
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
        self.url_input.textChanged.connect(self._on_url_changed)
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

        # --- Provider + API key ---
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("Model:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Gemini", Provider.GEMINI)
        self.provider_combo.addItem("Claude", Provider.CLAUDE)
        self.provider_combo.addItem("Ręczny", Provider.MANUAL)
        self.provider_combo.currentIndexChanged.connect(
            self._on_provider_changed
        )
        key_row.addWidget(self.provider_combo)

        self.key_label = QLabel("API Key:")
        key_row.addWidget(self.key_label)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
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

        # --- Przycisk zapisu ręcznego streszczenia ---
        self.save_manual_btn = QPushButton("Zapisz streszczenie")
        self.save_manual_btn.clicked.connect(self._on_save_manual)
        self.save_manual_btn.hide()
        layout.addWidget(self.save_manual_btn)

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

        # Provider
        provider_name = self.settings.value("provider", "gemini")
        idx = self.provider_combo.findData(Provider(provider_name))
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        # Klucze API (osobne dla każdego providera)
        gemini_key = self.settings.value("api_key_gemini", "")
        if not gemini_key:
            gemini_key = (
                os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
                or ""
            )
        claude_key = self.settings.value("api_key_claude", "")
        if not claude_key:
            claude_key = os.environ.get("ANTHROPIC_API_KEY") or ""

        self._api_keys = {
            Provider.GEMINI: gemini_key,
            Provider.CLAUDE: claude_key,
        }
        self._on_provider_changed()

        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def _current_provider(self) -> Provider:
        return self.provider_combo.currentData()

    def _on_provider_changed(self) -> None:
        # Zapisz bieżący klucz do słownika
        if hasattr(self, "_last_provider") and self._last_provider != Provider.MANUAL:
            self._api_keys[self._last_provider] = (
                self.key_input.text().strip()
            )

        provider = self._current_provider()
        self._last_provider = provider

        is_manual = provider == Provider.MANUAL
        self.key_label.setVisible(not is_manual)
        self.key_input.setVisible(not is_manual)

        if is_manual:
            self.start_btn.setText("Pobierz transkrypcję")
        else:
            self.start_btn.setText("Pobierz i streść")

        if provider == Provider.CLAUDE:
            self.key_label.setText("Anthropic API Key:")
            self.key_input.setPlaceholderText("Klucz API Claude")
        elif provider == Provider.GEMINI:
            self.key_label.setText("Gemini API Key:")
            self.key_input.setPlaceholderText("Klucz API Gemini")

        if not is_manual:
            self.key_input.setText(self._api_keys.get(provider, ""))

    def _save_settings(self) -> None:
        self.settings.setValue("output_dir", self.dir_input.text())
        self.settings.setValue(
            "provider", self._current_provider().value
        )
        # Upewnij się, że bieżący klucz jest zapisany
        self._api_keys[self._current_provider()] = (
            self.key_input.text().strip()
        )
        self.settings.setValue(
            "api_key_gemini", self._api_keys.get(Provider.GEMINI, "")
        )
        self.settings.setValue(
            "api_key_claude", self._api_keys.get(Provider.CLAUDE, "")
        )
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

        provider = self._current_provider()
        api_key = self.key_input.text().strip()
        if provider != Provider.MANUAL and not api_key:
            provider_label = (
                "Anthropic" if provider == Provider.CLAUDE else "Gemini"
            )
            QMessageBox.warning(
                self,
                "Brak klucza API",
                f"Podaj klucz {provider_label} API Key.",
            )
            self.key_input.setFocus()
            return

        self.transcript_view.clear()
        self.summary_view.clear()
        self.summary_view.setReadOnly(True)
        self.summary_view.setPlaceholderText("")
        self.save_manual_btn.hide()
        self.meta = None
        self.transcript_text = ""
        self.summary_text = ""
        self._set_busy(True)

        self._worker = TranscriptWorker(url)
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_transcript_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_url_changed(self, text: str) -> None:
        text = text.strip()
        if ("youtube.com/watch?v=" in text or "youtu.be/" in text) and self.start_btn.isEnabled():
            self._on_start()

    def _on_status(self, msg: str) -> None:
        self.status_label.setText(msg)

    def _on_transcript_done(self, text: str, meta) -> None:
        self.meta = meta
        self.transcript_text = text
        self.transcript_view.setPlainText(text)
        self.tabs.setCurrentIndex(0)

        # Zapisz transkrypcję
        self._save_transcript()

        provider = self._current_provider()
        if provider == Provider.MANUAL:
            # Tryb ręczny — użytkownik wkleja streszczenie
            self._set_busy(False)
            self.summary_view.setReadOnly(False)
            self.summary_view.clear()
            self.summary_view.setPlaceholderText(
                "Wklej tutaj streszczenie w Markdown..."
            )
            self.save_manual_btn.show()
            self.tabs.setCurrentIndex(1)
            self.summary_view.setFocus()
            self.status_label.setText(
                "Transkrypcja pobrana — wklej streszczenie"
            )
        else:
            # Tryb automatyczny — generuj streszczenie przez LLM
            api_key = self.key_input.text().strip()
            self._worker = SummaryWorker(
                text, api_key, self.meta, provider
            )
            self._worker.status.connect(self._on_status)
            self._worker.finished.connect(self._on_summary_done)
            self._worker.error.connect(self._on_error)
            self._worker.start()

    def _on_summary_done(self, summary: str) -> None:
        self.summary_text = summary
        self.summary_view.setReadOnly(True)
        self.summary_view.setMarkdown(summary)
        self.save_manual_btn.hide()
        self.tabs.setCurrentIndex(1)
        self._set_busy(False)

        # Zapisz streszczenie i otwórz w Typie
        summary_path = self._save_summary()
        if summary_path:
            self._open_in_typora(summary_path)

        self.status_label.setText("Gotowe — pliki zapisane")

    def _on_save_manual(self) -> None:
        """Zapisz ręcznie wklejone streszczenie z postprocessingiem."""
        raw = self.summary_view.toPlainText().strip()
        if not raw:
            QMessageBox.warning(
                self,
                "Brak streszczenia",
                "Wklej streszczenie przed zapisaniem.",
            )
            return

        summary = postprocess_summary(raw, self.meta)
        self._on_summary_done(summary)

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
    app.setDesktopFileName("transkrypcje-gui")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
