# Transkrypcje YouTube

Pobieranie transkrypcji filmów YouTube i generowanie streszczeń w Markdown
przy pomocy LLM (Gemini, Claude) lub ręcznie. Aplikacja desktopowa w PyQt6.

## Wymagania

### Narzędzia systemowe

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Typora](https://typora.io/) *(opcjonalnie)* — do automatycznego otwierania
  wygenerowanych plików `.md`; bez Typory używany jest `xdg-open`

### Klucz API

Co najmniej jeden z:

- `GEMINI_API_KEY` — Google Gemini
- `ANTHROPIC_API_KEY` — Anthropic Claude
- Żaden — w trybie ręcznym

## Instalacja

### Instalacja w systemie

```bash
./install.sh
```

Skrypt instaluje komendy globalnie (`uv tool install`), kopiuje ikonę
i wpis `.desktop`. Aplikacja pojawi się w menu systemowym.

Aktualizacja (po `git pull` lub zmianach w kodzie):

```bash
./install.sh
```

Odinstalowanie:

```bash
./install.sh --remove
```

### Tryb deweloperski (bez instalacji systemowej)

```bash
uv sync
uv run transkrypcje-gui
```

## GUI

Uruchom z menu systemowego lub komendą:

```bash
transkrypcje-gui [URL]
```

Podanie URL od razu wypełnia pole i rozpoczyna pobieranie.

### Tryby pracy

- **Gemini / Claude** — wklej URL, aplikacja pobierze transkrypcję
  i automatycznie wygeneruje streszczenie przez wybrany model LLM.
- **Ręczny** — aplikacja pobiera transkrypcję i udostępnia przycisk
  **Kopiuj prompt**, który kopiuje do schowka gotowy prompt
  z transkrypcją. Wklej go do dowolnego LLM, a otrzymane streszczenie
  wklej z powrotem do aplikacji i kliknij **Zapisz streszczenie**.

Pliki (transkrypcja `.txt` i streszczenie `.md`) zapisywane są
automatycznie w wybranym katalogu wyjściowym.

## CLI

```bash
# Transkrypcja na stdout
transkrypcja https://www.youtube.com/watch?v=VIDEO_ID

# Transkrypcja w konkretnym języku
transkrypcja https://www.youtube.com/watch?v=VIDEO_ID pl

# Streszczenie przez Gemini (domyślnie)
GEMINI_API_KEY=... streszczenie https://www.youtube.com/watch?v=VIDEO_ID

# Streszczenie przez Claude
ANTHROPIC_API_KEY=... streszczenie --claude https://www.youtube.com/watch?v=VIDEO_ID
```

W trybie deweloperskim zamiast `transkrypcja` użyj `uv run transkrypcja` itd.

## Znane problemy

### „Sign in to confirm you're not a bot"

Przy pobieraniu metadanych filmu YouTube może odrzucić żądanie komunikatem:

```
ERROR: [youtube] ...: Sign in to confirm you're not a bot.
```

To zabezpieczenie antybotowe YouTube. Najczęstsza przyczyna: **przestarzała
wersja yt-dlp**. YouTube regularnie zmienia mechanizmy wykrywania botów,
a yt-dlp wydaje poprawki, które je omijają — dlatego yt-dlp trzeba co jakiś
czas aktualizować.

**Rozwiązanie:** zaktualizuj aplikację, uruchamiając ponownie skrypt
instalacyjny z katalogu projektu:

```bash
./install.sh
```

Skrypt przeinstalowuje aplikację (`uv tool install --reinstall`), pobierając
przy tym najnowszą wersję yt-dlp z PyPI.

Uwagi:

- Wersja yt-dlp z repozytorium dystrybucji **nie ma znaczenia** — aplikacja
  używa wyłącznie wersji z PyPI, zainstalowanej przez uv w izolowanym
  środowisku (`~/.local/share/uv/tools/transkrypcje`). Środowisko to jest
  zamrożone w momencie instalacji, dlatego samo wydanie nowej wersji yt-dlp
  nic nie zmienia bez przeinstalowania.
- Środowisko deweloperskie (`uv run ...`) aktualizuje się osobno:
  `uv lock --upgrade-package yt-dlp`.
- Jeśli po aktualizacji błąd nie znika, blokada może dotyczyć adresu IP
  (np. VPN, sieć współdzielona) — wtedy pomaga zmiana sieci lub przekazanie
  yt-dlp cookies zalogowanej przeglądarki (planowane rozszerzenie, patrz
  BACKLOG).
