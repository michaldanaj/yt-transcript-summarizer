"""Pobieranie transkrypcji i rozdziałów z YouTube."""

import re
from datetime import date

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """Wyciąga ID filmu z URL-a YouTube."""
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return url


def format_timestamp(seconds: float) -> str:
    """Zamienia sekundy na format MM:SS lub HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def timestamp_to_seconds(ts: str) -> int:
    """Zamienia MM:SS lub HH:MM:SS na liczbę sekund."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])


def linkify_timestamps(text: str, video_id: str) -> str:
    """Zamienia [MM:SS] i [HH:MM:SS] na linki do YouTube."""
    pattern = r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]"

    def replace(m: re.Match) -> str:
        ts = m.group(1)
        seconds = timestamp_to_seconds(ts)
        url = f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
        return f"[{ts}]({url})"

    return re.sub(pattern, replace, text)


class VideoMeta:
    """Metadane filmu YouTube."""

    def __init__(
        self,
        video_id: str,
        title: str,
        channel: str,
        channel_url: str,
        video_url: str,
        upload_date: str,
        chapters: list[dict],
    ):
        self.video_id = video_id
        self.title = title
        self.channel = channel
        self.channel_url = channel_url
        self.video_url = video_url
        self.upload_date = upload_date   # format: YYYY-MM-DD
        self.chapters = chapters

    def safe_filename(self, suffix: str = "") -> str:
        """Zwraca bezpieczną nazwę pliku: tytuł - kanał[suffix]."""
        name = f"{self.title} - {self.channel}"
        for ch in r'<>:"/\|?*':
            name = name.replace(ch, "")
        name = name.strip(". ")
        if suffix:
            name = f"{name}{suffix}"
        return name

    def format_header(self) -> str:
        """Nagłówek Markdown z metadanymi (linki, daty)."""
        today = date.today().isoformat()
        lines = [
            f"**Film:** [{self.title}]({self.video_url})  ",
            f"**Kanał:** [{self.channel}]({self.channel_url})  ",
            f"**Data publikacji:** {self.upload_date}  ",
            f"**Data wygenerowania:** {today}  ",
        ]
        return "\n".join(lines)


def fetch_meta(video_id: str) -> VideoMeta:
    """Pobiera metadane filmu przez yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {"skip_download": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        raw_date = info.get("upload_date", "")
        if len(raw_date) == 8:
            upload_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
        else:
            upload_date = raw_date or "nieznana"

        channel_url = (
            info.get("uploader_url")
            or info.get("channel_url")
            or ""
        )

        return VideoMeta(
            video_id=video_id,
            title=info.get("title", video_id),
            channel=info.get("channel", info.get("uploader", "unknown")),
            channel_url=channel_url,
            video_url=info.get("webpage_url", url),
            upload_date=upload_date,
            chapters=info.get("chapters") or [],
        )


def fetch_transcript(video_id: str, lang: str | None = None) -> tuple[list, str, str]:
    """
    Pobiera transkrypcję dla podanego ID filmu.

    Zwraca (snippets, language_name, language_code).
    Preferuje język: podany → pl → en → pierwszy dostępny.
    """
    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.list(video_id)
    available = list(transcript_list)

    if lang:
        transcript = transcript_list.find_transcript([lang])
    else:
        try:
            transcript = transcript_list.find_transcript(["pl"])
        except Exception:
            try:
                transcript = transcript_list.find_transcript(["en"])
            except Exception:
                transcript = available[0]

    snippets = transcript.fetch()
    return snippets, transcript.language, transcript.language_code


def available_languages(video_id: str) -> list[tuple[str, str]]:
    """Zwraca listę (language_code, language_name) dla danego filmu."""
    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.list(video_id)
    return [(t.language_code, t.language) for t in transcript_list]


def format_transcript(snippets: list, meta: VideoMeta) -> str:
    """Formatuje snippety do tekstu z nagłówkiem, timestampami i rozdziałami."""
    lines = [meta.format_header(), ""]

    # Spis treści
    if meta.chapters:
        lines.append("## Spis treści")
        lines.append("")
        for i, ch in enumerate(meta.chapters, 1):
            ts = format_timestamp(ch["start_time"])
            lines.append(f"  {i:2d}. [{ts}] {ch['title']}")
        lines.append("")

    lines.append("## Transkrypcja")
    lines.append("")

    # Indeks: numer snippetu → rozdział który się tu zaczyna
    chapter_starts: dict[int, dict] = {}
    if meta.chapters:
        ch_idx = 0
        for si, snippet in enumerate(snippets):
            while (
                ch_idx < len(meta.chapters)
                and snippet.start >= meta.chapters[ch_idx]["start_time"]
            ):
                chapter_starts[si] = meta.chapters[ch_idx]
                ch_idx += 1

    for si, snippet in enumerate(snippets):
        if si in chapter_starts:
            ch = chapter_starts[si]
            ts = format_timestamp(ch["start_time"])
            lines.append(f"\n### [{ts}] {ch['title']}\n")
        ts = format_timestamp(snippet.start)
        lines.append(f"[{ts}] {snippet.text}")

    return "\n".join(lines)


def get_full_transcript(url: str, lang: str | None = None) -> tuple[str, VideoMeta]:
    """Pobiera i formatuje pełną transkrypcję dla URL-a.

    Zwraca (sformatowana_transkrypcja, metadane_filmu).
    """
    video_id = extract_video_id(url)
    meta = fetch_meta(video_id)
    snippets, _, _ = fetch_transcript(video_id, lang)
    return format_transcript(snippets, meta), meta


def main() -> None:
    import sys

    if len(sys.argv) < 2:
        print("Użycie: transkrypcja <URL_lub_ID_filmu> [kod_języka]")
        print("Przykład: transkrypcja https://www.youtube.com/watch?v=UabBYexBD4k pl")
        sys.exit(1)

    video_id = extract_video_id(sys.argv[1])
    lang = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Pobieram transkrypcję dla filmu: {video_id}", file=sys.stderr)

    meta = fetch_meta(video_id)
    snippets, lang_name, lang_code = fetch_transcript(video_id, lang)

    langs = available_languages(video_id)
    print(
        f"Dostępne transkrypcje: {', '.join(c for c, _ in langs)}",
        file=sys.stderr,
    )
    print(f"Wybrana transkrypcja: {lang_name} ({lang_code})", file=sys.stderr)

    print(format_transcript(snippets, meta))


if __name__ == "__main__":
    main()
