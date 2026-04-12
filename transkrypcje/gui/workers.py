"""Workery QThread do operacji w tle."""

from PyQt6.QtCore import QThread, pyqtSignal

from ..transcript import (
    VideoMeta,
    extract_video_id,
    fetch_meta,
    fetch_transcript,
    format_transcript,
)
from ..summarizer import summarize


class TranscriptWorker(QThread):
    """Pobiera metadane + transkrypcję w tle."""

    finished = pyqtSignal(str, VideoMeta)  # (formatted_transcript, meta)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, url: str, lang: str | None = None) -> None:
        super().__init__()
        self.url = url
        self.lang = lang

    def run(self) -> None:
        try:
            video_id = extract_video_id(self.url)

            self.status.emit("Pobieram metadane filmu...")
            meta = fetch_meta(video_id)

            self.status.emit(f"Pobieram transkrypcję: {meta.title}...")
            snippets, _, _ = fetch_transcript(video_id, self.lang)

            text = format_transcript(snippets, meta.chapters)
            self.finished.emit(text, meta)
        except Exception as e:
            self.error.emit(str(e))


class SummaryWorker(QThread):
    """Generuje streszczenie w tle."""

    finished = pyqtSignal(str)  # summary markdown
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, transcript: str, api_key: str) -> None:
        super().__init__()
        self.transcript = transcript
        self.api_key = api_key

    def run(self) -> None:
        try:
            self.status.emit("Generuję streszczenie (Gemini)...")
            result = summarize(self.transcript, self.api_key)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
