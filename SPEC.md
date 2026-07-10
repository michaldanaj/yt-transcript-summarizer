# Specyfikacja — Transkrypcje YouTube

## Cel

Aplikacja desktopowa (Linux, PyQt6) do pobierania transkrypcji filmów YouTube i
generowania ich streszczeń w Markdown przy pomocy LLM (Gemini, Claude) lub
ręcznego wklejania streszczeń.

---

## Widok główny

Jedno okno (`MainWindow`) z pionowym układem elementów.

### Wiersz URL

- Pole tekstowe: URL filmu YouTube
- Przycisk **Pobierz i streść** (w trybie ręcznym: **Pobierz transkrypcję**)
- Wklejenie linku YouTube automatycznie rozpoczyna pobieranie
- Przy starcie aplikacji: jeśli schowek systemowy zawiera link YouTube, jest
  automatycznie wklejany do pola URL i pobieranie rozpoczyna się bez działania
  użytkownika

### Wiersz katalogu wyjściowego

- Pole tekstowe (read-only) z bieżącą ścieżką
- Przycisk **Zmień…** → `QFileDialog`

### Wiersz modelu i klucza API

- Dropdown **Model**: Gemini / Claude / Ręczny
- Pole **API Key** (hasło) — ukrywane w trybie ręcznym
- Po ukryciu pola API Key w trybie ręcznym, przycisk Model nie powinien zmieniać rozmiaru i pozycji
- Etykieta klucza zmienia się dynamicznie (Gemini API Key / Anthropic API Key)
- Klucze API przechowywane osobno dla każdego providera w `QSettings`
- Fallback na zmienne środowiskowe: `GEMINI_API_KEY` / `GOOGLE_API_KEY`,
  `ANTHROPIC_API_KEY`

### Zakładki

**Zakładka Transkrypcja**

- `QTextEdit` (read-only, monospace) z pełną transkrypcją:
    - nagłówek z metadanymi (tytuł, kanał, data publikacji, URL)
    - spis treści rozdziałów (jeśli film je posiada)
    - tekst z timestampami i nagłówkami rozdziałów
- Transkrypcja zapisywana automatycznie jako `<tytuł> - <kanał>_transcript.txt`

**Zakładka Streszczenie**

- `QTextEdit` ze streszczeniem (renderowany Markdown)
- W trybie ręcznym — edytowalny, z placeholderem „Wklej tutaj streszczenie w
  Markdown…"
- Streszczenie zapisywane automatycznie jako `<tytuł> - <kanał>.md`

### Przyciski trybu ręcznego

Widoczne tylko w trybie ręcznym, po pobraniu transkrypcji:

- **Kopiuj prompt** — kopiuje do schowka pełny prompt (instrukcja +
  transkrypcja), gotowy do wklejenia w zewnętrznym LLM
- **Zapisz streszczenie** — uruchamia postprocessing wklejonego tekstu i zapis

### Pasek statusu

- Komunikaty o postępie (pobieranie, generowanie, kopiowanie promptu)
- Po wklejeniu streszczenia w trybie ręcznym, powinien zniknąć komunikat mówiący o możliwości pobrania prompt i streszczeniu
- Etykieta statystyk transkrypcji: liczba słów i linii (po pobraniu)
- Nieokreślony pasek postępu (`QProgressBar`) podczas operacji sieciowych

---

## Tryby pracy

### Automatyczny (Gemini / Claude)

Używane modele (na stałe w kodzie): `gemini-3.5-flash` (Gemini),
`claude-sonnet-4-6` (Claude).

1. Użytkownik wkleja URL → automatyczne pobieranie transkrypcji
2. Po pobraniu transkrypcji → automatyczne generowanie streszczenia przez LLM
3. Streszczenie zapisywane do pliku i otwierane w Typorze (lub domyślnej
   aplikacji przez `xdg-open`)

### Ręczny

1. Użytkownik wkleja URL → pobieranie transkrypcji (bez klucza API)
2. Zakładka streszczenia staje się edytowalna
3. Użytkownik może kliknąć **Kopiuj prompt** → wkleić do zewnętrznego LLM
4. Po wklejeniu odpowiedzi, streszczenie automatycznie się zapisuje, ale wciąż
   użytkownik może kliknąć **Zapisz streszczenie**
5. Postprocessing (zawijanie Markdown, linkowanie timestampów, nagłówek z
   metadanymi) i zapis jak w trybie automatycznym

---

## Postprocessing streszczenia

Każde streszczenie (automatyczne i ręczne) przechodzi tę samą obróbkę:

1. `_strip_code_fence` — usunięcie owijającej ramki ` ```markdown … ``` ` jeśli
   LLM ją dodał
2. `wrap_markdown` — zawijanie wierszy do 79 znaków z zachowaniem struktury
   Markdown (nagłówki, listy, bloki kodu, wzory LaTeX)
3. `linkify_timestamps` — zamiana timestampów na linki do YouTube
4. Dodanie nagłówka z metadanymi filmu (tytuł, kanał, data, URL)

---

## Ustawienia (QSettings)

Zapisywane automatycznie przy zamknięciu okna:

| Parametr         | Opis                                        |
| ---------------- | ------------------------------------------- |
| `output_dir`     | Katalog wyjściowy (domyślnie `~/Dokumenty`) |
| `provider`       | Wybrany provider (gemini / claude / manual) |
| `api_key_gemini` | Klucz API Gemini                            |
| `api_key_claude` | Klucz API Claude                            |
| `geometry`       | Pozycja i rozmiar okna                      |

---

## Operacje asynchroniczne

Pobieranie transkrypcji (`TranscriptWorker`) i generowanie streszczenia
(`SummaryWorker`) odbywają się w `QThread`. W tym czasie:

- Pole URL i przycisk start są zablokowane
- Wyświetlany jest pasek postępu i komunikat w pasku statusu

---

## Obsługa błędów

| Błąd                                                   | Komunikat                                                          |
| ------------------------------------------------------ | ------------------------------------------------------------------ |
| Brak klucza API                                        | „Podaj klucz {provider} API Key." (przed startem, walidacja w GUI) |
| Nieprawidłowy URL, brak transkrypcji, błąd sieci / API | Komunikat wyjątku z biblioteki w `QMessageBox.critical`            |
| Weryfikacja antybotowa YouTube (yt-dlp)                | Dedykowany komunikat `BotCheckError` — patrz niżej                 |

### Weryfikacja antybotowa YouTube (yt-dlp)

Pobieranie metadanych (`fetch_meta`) może zakończyć się błędem YouTube
„Sign in to confirm you're not a bot". Najczęstsza przyczyna: przestarzała
wersja yt-dlp — YouTube regularnie zmienia mechanizmy antybotowe, a yt-dlp
wydaje poprawki, które je omijają (aktualizacja yt-dlp jest pierwszą linią
obrony).

Zachowanie aplikacji:

1. `fetch_meta` przechwytuje `yt_dlp.utils.DownloadError`. Jeśli komunikat
   zawiera sygnaturę bot-checku (fraza „Sign in to confirm"), zgłasza
   dedykowany wyjątek `BotCheckError` (zdefiniowany w `transcript.py`).
2. Komunikat wyjątku jest po polsku i zawiera:
   - wyjaśnienie przyczyny (YouTube zablokował żądanie jako podejrzane;
     zwykle winna jest przestarzała wersja yt-dlp),
   - instrukcję aktualizacji: ponowne uruchomienie `./install.sh`
     z katalogu projektu (patrz „Procedura aktualizacji" niżej),
   - odesłanie do sekcji „Znane problemy" w README.
3. GUI: komunikat trafia istniejącą ścieżką (sygnał `error` workera →
   `_on_error`) do `QMessageBox.critical` — bez surowego tracebacku.
4. CLI (`transkrypcja`, `streszczenie`): komunikat wypisywany na stderr,
   wyjście z kodem 1, bez tracebacku.
5. Pozostałe `DownloadError` przechodzą bez zmian (obecne zachowanie).

### Procedura aktualizacji yt-dlp

Aplikacja jest zainstalowana przez `uv tool install` (skrypt `install.sh`)
w izolowanym środowisku `~/.local/share/uv/tools/transkrypcje`. To środowisko
**nie korzysta z `uv.lock`** — zależności są rozwiązywane z `pyproject.toml`
w momencie instalacji i pozostają zamrożone aż do reinstalacji.

Aktualizacja zainstalowanej aplikacji (wraz z yt-dlp):

```bash
cd <katalog projektu> && ./install.sh
```

Skrypt wykrywa istniejącą instalację i wykonuje `uv tool install
--reinstall`, co ponownie rozwiązuje zależności i pobiera najnowszą wersję
yt-dlp dopuszczoną przez `pyproject.toml` (`yt-dlp>=...`).

Środowisko deweloperskie (`.venv`, `uv run`) aktualizuje się osobno:

```bash
uv lock --upgrade-package yt-dlp
```

Procedura jest opisana także w README (sekcja „Znane problemy"), wraz z
uwagą, że wersja yt-dlp z repozytorium dystrybucji nie ma znaczenia —
aplikacja używa wyłącznie wersji z PyPI zainstalowanej przez uv.

Poza zakresem (pozostaje w backlogu jako możliwe rozszerzenie): cookies
z przeglądarki (`cookiesfrombrowser`) oraz fallback metadanych przez oEmbed.

---

## CLI

```
transkrypcja <URL> [kod_języka]             # pobierz transkrypcję
streszczenie [--claude] <URL> [kod_języka]  # wygeneruj streszczenie
transkrypcje-gui [URL]                      # uruchom GUI (opcjonalnie z URL)
```

Podanie URL jako argumentu wypełnia pole i automatycznie rozpoczyna pobieranie,
identycznie jak ręczne wklejenie URL w aplikacji.

---

## Moduły

```
transkrypcje/
├── transcript.py      # extract_video_id, fetch_meta, fetch_transcript,
│                      #   available_languages, format_transcript,
│                      #   get_full_transcript, linkify_timestamps,
│                      #   VideoMeta, BotCheckError
├── summarizer.py      # Provider, PROMPT, summarize, postprocess_summary,
│                      #   wrap_markdown
└── gui/
    ├── app.py         # MainWindow, main()
    └── workers.py     # TranscriptWorker, SummaryWorker
```

### Zasady importów

- `anthropic` i `google-genai` są importowane **leniwie** (wewnątrz
  `_summarize_claude` / `_summarize_gemini`), a nie na poziomie modułu —
  dzięki temu GUI uruchamia się szybko bez ładowania ciężkich bibliotek SDK
  przy każdym starcie.

---

## Technologie

### Zależności Python (zarządzane przez uv)

| Rola                           | Biblioteka             |
| ------------------------------ | ---------------------- |
| GUI                            | PyQt6                  |
| Transkrypcje                   | youtube-transcript-api |
| Metadane YT (rozdziały, tytuł) | yt-dlp                 |
| LLM — Gemini                   | google-genai           |
| LLM — Claude                   | anthropic              |

### Zależności systemowe

| Narzędzie  | Rola                                                          | Wymagane       |
| ---------- | ------------------------------------------------------------- | -------------- |
| Python 3.12+ | Środowisko uruchomieniowe                                   | tak            |
| uv         | Zarządzanie środowiskiem Python i instalacja aplikacji        | tak            |
| Typora     | Automatyczne otwieranie wygenerowanych plików `.md`           | nie (fallback: `xdg-open`) |
