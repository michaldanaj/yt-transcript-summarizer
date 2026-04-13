# Specyfikacja — Transkrypcje YouTube

## Cel

Aplikacja desktopowa (Linux, PyQt6) do pobierania transkrypcji filmów YouTube
i generowania ich streszczeń w Markdown przy pomocy LLM (Gemini, Claude)
lub ręcznego wklejania streszczeń.

---

## Widok główny

Jedno okno (`MainWindow`) z pionowym układem elementów.

### Wiersz URL

- Pole tekstowe: URL filmu YouTube
- Przycisk **Pobierz i streść** (w trybie ręcznym: **Pobierz transkrypcję**)
- Wklejenie linku YouTube automatycznie rozpoczyna pobieranie

### Wiersz katalogu wyjściowego

- Pole tekstowe (read-only) z bieżącą ścieżką
- Przycisk **Zmień…** → `QFileDialog`

### Wiersz modelu i klucza API

- Dropdown **Model**: Gemini / Claude / Ręczny
- Pole **API Key** (hasło) — ukrywane w trybie ręcznym
- Etykieta klucza zmienia się dynamicznie (Gemini API Key / Anthropic API Key)
- Klucze API przechowywane osobno dla każdego providera w `QSettings`
- Fallback na zmienne środowiskowe: `GEMINI_API_KEY` / `GOOGLE_API_KEY`,
  `ANTHROPIC_API_KEY`

### Zakładki

**Zakładka Transkrypcja**

- `QTextEdit` (read-only, monospace) z pełną transkrypcją:
  - spis treści rozdziałów (jeśli film je posiada)
  - tekst z timestampami i nagłówkami rozdziałów
- Transkrypcja zapisywana automatycznie jako `<tytuł>_transcript.txt`

**Zakładka Streszczenie**

- `QTextEdit` ze streszczeniem (renderowany Markdown)
- W trybie ręcznym — edytowalny, z placeholderem
  „Wklej tutaj streszczenie w Markdown…"
- Streszczenie zapisywane automatycznie jako `<tytuł>.md`

### Przyciski trybu ręcznego

Widoczne tylko w trybie ręcznym, po pobraniu transkrypcji:

- **Kopiuj prompt** — kopiuje do schowka pełny prompt (instrukcja + transkrypcja),
  gotowy do wklejenia w zewnętrznym LLM
- **Zapisz streszczenie** — uruchamia postprocessing wklejonego tekstu i zapis

### Pasek statusu

- Komunikaty o postępie (pobieranie, generowanie, kopiowanie promptu)
- Nieokreślony pasek postępu (`QProgressBar`) podczas operacji sieciowych

---

## Tryby pracy

### Automatyczny (Gemini / Claude)

1. Użytkownik wkleja URL → automatyczne pobieranie transkrypcji
2. Po pobraniu transkrypcji → automatyczne generowanie streszczenia przez LLM
3. Streszczenie zapisywane do pliku i otwierane w Typorze (lub domyślnej
   aplikacji przez `xdg-open`)

### Ręczny

1. Użytkownik wkleja URL → pobieranie transkrypcji (bez klucza API)
2. Zakładka streszczenia staje się edytowalna
3. Użytkownik może kliknąć **Kopiuj prompt** → wkleić do zewnętrznego LLM
4. Po wklejeniu odpowiedzi klika **Zapisz streszczenie**
5. Postprocessing (zawijanie Markdown, linkowanie timestampów, nagłówek
   z metadanymi) i zapis jak w trybie automatycznym

---

## Postprocessing streszczenia

Każde streszczenie (automatyczne i ręczne) przechodzi tę samą obróbkę:

1. `wrap_markdown` — zawijanie wierszy do 79 znaków z zachowaniem
   struktury Markdown (nagłówki, listy, bloki kodu, wzory LaTeX)
2. `linkify_timestamps` — zamiana timestampów na linki do YouTube
3. Dodanie nagłówka z metadanymi filmu (tytuł, kanał, data, URL)

---

## Ustawienia (QSettings)

Zapisywane automatycznie przy zamknięciu okna:

| Parametr | Opis |
|---|---|
| `output_dir` | Katalog wyjściowy (domyślnie `~/Dokumenty`) |
| `provider` | Wybrany provider (gemini / claude / manual) |
| `api_key_gemini` | Klucz API Gemini |
| `api_key_claude` | Klucz API Claude |
| `geometry` | Pozycja i rozmiar okna |

---

## Operacje asynchroniczne

Pobieranie transkrypcji (`TranscriptWorker`) i generowanie streszczenia
(`SummaryWorker`) odbywają się w `QThread`. W tym czasie:

- Pole URL i przycisk start są zablokowane
- Wyświetlany jest pasek postępu i komunikat w pasku statusu

---

## Obsługa błędów

| Błąd | Komunikat |
|---|---|
| Nieprawidłowy URL | „Nieprawidłowy URL lub ID filmu" |
| Brak transkrypcji | „Film nie posiada transkrypcji w wybranym języku" |
| Brak klucza API | „Podaj klucz {provider} API Key." |
| Błąd sieci / API | Szczegóły w oknie dialogowym `QMessageBox.critical` |

---

## CLI

```
transkrypcja <URL> [kod_języka]             # pobierz transkrypcję
streszczenie [--claude] <URL> [kod_języka]  # wygeneruj streszczenie
transkrypcje-gui                            # uruchom GUI
```

---

## Moduły

```
transkrypcje/
├── transcript.py      # extract_video_id, fetch_meta, fetch_transcript,
│                      #   available_languages, format_transcript,
│                      #   get_full_transcript, linkify_timestamps,
│                      #   VideoMeta
├── summarizer.py      # Provider, PROMPT, summarize, postprocess_summary,
│                      #   wrap_markdown
└── gui/
    ├── app.py         # MainWindow, main()
    └── workers.py     # TranscriptWorker, SummaryWorker
```

---

## Technologie

| Rola | Biblioteka |
|---|---|
| GUI | PyQt6 |
| Transkrypcje | youtube-transcript-api |
| Metadane YT (rozdziały, tytuł) | yt-dlp |
| LLM — Gemini | google-genai |
| LLM — Claude | anthropic |
| Zarządzanie środowiskiem | uv |
