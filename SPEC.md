# Specyfikacja — Transkrypcje YouTube

## Cel

Aplikacja desktopowa (Linux, PyQt6) do pobierania transkrypcji filmów YouTube
i generowania ich streszczeń w Markdown przy pomocy Gemini LLM.

---

## Widok główny

### Panel wejściowy (górna belka)

- Pole tekstowe: URL lub ID filmu YouTube
- Przycisk **Pobierz transkrypcję**
- Dropdown: wybór języka transkrypcji (wypełniany po pobraniu listy dostępnych)
- Przycisk **Generuj streszczenie** (aktywny po pobraniu transkrypcji)

### Panel główny (zakładki lub split-view)

**Zakładka Transkrypcja**

- Widok tekstowy (read-only) z pełną transkrypcją:
  - spis treści rozdziałów (jeśli film je posiada)
  - tekst z timestampami i nagłówkami rozdziałów
- Przycisk **Zapisz transkrypcję** → plik `.txt`

**Zakładka Streszczenie**

- Widok Markdown (renderowany) ze streszczeniem
- Przełącznik: podgląd renderowany / źródło Markdown
- Przycisk **Zapisz streszczenie** → plik `.md`

### Pasek statusu (dół)

- Komunikaty o postępie (pobieranie, generowanie)
- Wskaźnik aktywności (spinner) podczas operacji sieciowych

---

## Ustawienia

Dostępne przez menu **Ustawienia** lub przycisk w pasku narzędzi.

| Parametr | Opis |
|---|---|
| `GEMINI_API_KEY` | Klucz API Gemini (zapisywany w keyring systemu) |
| Model Gemini | Wybór modelu (domyślnie `gemini-2.5-flash`) |
| Preferowany język | Domyślny język transkrypcji (domyślnie: `pl`) |
| Szerokość zawijania | Długość wiersza w eksportowanym Markdown (domyślnie: 79) |

---

## Operacje asynchroniczne

Pobieranie transkrypcji i generowanie streszczenia odbywają się w tle
(`QThread` lub `asyncio`), żeby nie blokować GUI. W tym czasie:

- Pola wejściowe są zablokowane
- Wyświetlany jest spinner i komunikat w pasku statusu
- Dostępny przycisk **Anuluj**

---

## Obsługa błędów

| Błąd | Komunikat |
|---|---|
| Nieprawidłowy URL | „Nieprawidłowy URL lub ID filmu" |
| Brak transkrypcji | „Film nie posiada transkrypcji w wybranym języku" |
| Brak klucza API | „Ustaw klucz GEMINI_API_KEY w Ustawieniach" |
| Błąd sieci | „Błąd połączenia: {szczegóły}" |
| Błąd Gemini API | „Błąd API Gemini: {szczegóły}" |

---

## Moduły

```
transkrypcje/
├── transcript.py      # pobieranie: extract_video_id, fetch_chapters,
│                      #   fetch_transcript, available_languages,
│                      #   format_transcript, get_full_transcript
├── summarizer.py      # streszczanie: summarize, wrap_markdown
└── gui/
    ├── app.py         # MainWindow, QApplication, entry point
    ├── panels.py      # TranscriptPanel, SummaryPanel
    ├── settings.py    # SettingsDialog
    └── workers.py     # QThread workery dla operacji asynchronicznych
```

---

## Technologie

| Rola | Biblioteka |
|---|---|
| GUI | PyQt6 |
| Transkrypcje | youtube-transcript-api |
| Metadane YT (rozdziały) | yt-dlp |
| LLM | google-genai (Gemini) |
| Zarządzanie środowiskiem | uv |
