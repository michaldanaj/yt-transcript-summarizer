# Transkrypcje YouTube

Pobieranie transkrypcji filmów YouTube i generowanie streszczeń w Markdown
przy pomocy Gemini LLM. Aplikacja desktopowa w PyQt6.

## Wymagania

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Klucz API Gemini (`GEMINI_API_KEY`)

## Instalacja

### Tryb deweloperski (bez instalacji systemowej)

```bash
uv sync
uv run transkrypcje-gui
```

### Instalacja w systemie

Instaluje komendy globalnie — dostępne z dowolnego miejsca:

```bash
uv tool install .
transkrypcje-gui
```

Aktualizacja po zmianach w kodzie:

```bash
uv tool install . --force
```

Odinstalowanie:

```bash
uv tool uninstall transkrypcje
```

## Użycie CLI

```bash
# Transkrypcja na stdout
uv run transkrypcja https://www.youtube.com/watch?v=VIDEO_ID

# Transkrypcja w konkretnym języku
uv run transkrypcja https://www.youtube.com/watch?v=VIDEO_ID en

# Streszczenie na stdout
GEMINI_API_KEY=... uv run streszczenie https://www.youtube.com/watch?v=VIDEO_ID

# Streszczenie do pliku
GEMINI_API_KEY=... uv run streszczenie https://... > streszczenie.md
```
