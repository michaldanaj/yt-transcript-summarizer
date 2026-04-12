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

## Git

Każda logicznie spójna zmiana powinna być commitowana od razu po jej
wprowadzeniu. Nie czekaj na koniec sesji. Zasady:

- Commituj po każdej zakończonej zmianie (nowa funkcja, poprawka, refaktor).
- Jedno commit = jedna zmiana logiczna; nie mieszaj niezwiązanych rzeczy.
- Komunikat po polsku, zwięzły, opisuje *co i dlaczego* (nie *jak*).
- Zawsze dodawaj `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

## Zależności zewnętrzne

- `youtube-transcript-api` — transkrypcje
- `yt-dlp` — metadane (rozdziały, tytuł)
- `google-genai` — Gemini API
- `PyQt6` — GUI

## Wersjonowanie

Przy każdej zmianie kodu należy podbić wersję w `pyproject.toml`:

- patch (0.x.**Y**) — poprawki błędów, drobne zmiany
- minor (0.**X**.0) — nowe funkcje

## Zasady pracy z kodem

- Logika core (`transcript.py`, `summarizer.py`) nie importuje Qt.
- GUI (`gui/`) importuje core, nigdy odwrotnie.
- Testy uruchamiamy przez `uv run pytest`.
- Długość wiersza: 88 znaków (black-compatible).
- Specyfikacja aplikacji: `SPEC.md`.
