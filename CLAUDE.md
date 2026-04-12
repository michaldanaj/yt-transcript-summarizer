# CLAUDE.md

## Projekt

Aplikacja do pobierania transkrypcji filmów YouTube i generowania streszczeń
w Markdown przy pomocy Gemini LLM. Docelowo posiada GUI w PyQt6.

## Środowisko

Używamy `uv`. Nigdy nie używaj `pip` bezpośrednio.

```fish
uv run transkrypcja <URL>          # pobierz transkrypcję
uv run streszczenie <URL>          # wygeneruj streszczenie
uv run transkrypcje-gui            # uruchom GUI
```

Klucz API Gemini: zmienna środowiskowa `GEMINI_API_KEY`.

## Struktura pakietu

```
transkrypcje/
├── transcript.py      # logika pobierania transkrypcji i rozdziałów
├── summarizer.py      # logika streszczania (Gemini) + wrap_markdown
└── gui/
    └── app.py         # aplikacja Qt
```

Stare pliki `main.py` i `summarize.py` w korzeniu są przestarzałe —
logika przeniesiona do pakietu `transkrypcje/`.

## Zależności zewnętrzne

- `youtube-transcript-api` — transkrypcje
- `yt-dlp` — metadane (rozdziały, tytuł)
- `google-genai` — Gemini API
- `PyQt6` — GUI

## Zasady pracy z kodem

- Logika core (`transcript.py`, `summarizer.py`) nie importuje Qt.
- GUI (`gui/`) importuje core, nigdy odwrotnie.
- Testy uruchamiamy przez `uv run pytest`.
- Długość wiersza: 88 znaków (black-compatible).
- Specyfikacja aplikacji: `SPEC.md`.
