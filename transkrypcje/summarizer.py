"""Streszczanie transkrypcji przy użyciu Gemini LLM."""

import re
import textwrap

from google import genai

from .transcript import get_full_transcript

PROMPT = """\
Poniżej znajduje się transkrypcja filmu z YouTube. Na jej podstawie napisz \
streszczenie w języku polskim, w formacie Markdown.

Streszczenie powinno zawierać:
1. **Tytuł** — krótki, opisowy tytuł streszczenia (nagłówek H1)
2. **Główne tezy** — sekcja z kluczowymi punktami filmu (lista)
3. **Streszczenie** — pełne streszczenie filmu, podzielone na sekcje \
odpowiadające rozdziałom (jeśli są). Każda sekcja powinna mieć nagłówek H2 \
z timestampem.
4. **Wnioski** — krótkie podsumowanie najważniejszych wniosków

Wzory matematyczne zapisuj w notacji LaTeX: `$...$` dla wzorów w tekście \
(inline) i `$$...$$` dla wzorów blokowych.

Pisz zwięźle, ale nie pomijaj istotnych informacji. Zachowaj timestampy \
przy kluczowych momentach.

TRANSKRYPCJA:
{transcript}
"""

_NBSP = "\u00a0"


def _protect_inline_math(text: str) -> str:
    """Zamienia spacje wewnątrz $...$ na niełamliwe."""
    return re.sub(
        r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)",
        lambda m: "$" + m.group(1).replace(" ", _NBSP) + "$",
        text,
    )


def _restore_inline_math(text: str) -> str:
    return text.replace(_NBSP, " ")


def wrap_markdown(text: str, width: int = 79) -> str:
    """Łamie wiersze w Markdown do zadanej szerokości."""
    lines = text.split("\n")
    result = []
    in_code_block = False

    for line in lines:
        # Bloki kodu i wzory blokowe — nie zawijaj
        if line.startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            continue
        if line.startswith("$$"):
            in_code_block = not in_code_block
            result.append(line)
            continue
        if in_code_block:
            result.append(line)
            continue

        # Puste wiersze, nagłówki, krótkie wiersze — zostaw
        if len(line) <= width or line == "" or line.startswith("#"):
            result.append(line)
            continue

        # Elementy list — zachowaj wcięcie i prefix
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        list_prefixes = ("- ", "* ", "+ ")
        numbered = False
        prefix = indent

        for lp in list_prefixes:
            if stripped.startswith(lp):
                prefix = indent + lp
                stripped = stripped[len(lp):]
                break
        else:
            parts = stripped.split(". ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                prefix = indent + parts[0] + ". "
                stripped = parts[1]
                numbered = True

        if prefix != indent or numbered:
            subsequent_indent = " " * len(prefix)
            wrapped = textwrap.fill(
                _protect_inline_math(stripped),
                width=width,
                initial_indent=prefix,
                subsequent_indent=subsequent_indent,
            )
        else:
            wrapped = textwrap.fill(_protect_inline_math(line), width=width)

        result.append(_restore_inline_math(wrapped))

    return "\n".join(result)


def summarize(transcript: str, api_key: str) -> str:
    """Wysyła transkrypcję do Gemini i zwraca streszczenie w Markdown."""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROMPT.format(transcript=transcript),
    )
    return wrap_markdown(response.text)


def main() -> None:
    import os
    import sys

    if len(sys.argv) < 2:
        print("Użycie: streszczenie <URL_filmu> [kod_języka]")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Błąd: ustaw zmienną GEMINI_API_KEY lub GOOGLE_API_KEY")
        sys.exit(1)

    url = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else None

    print("Pobieram transkrypcję...", file=sys.stderr)
    transcript = get_full_transcript(url, lang)

    print("Generuję streszczenie...", file=sys.stderr)
    print(summarize(transcript, api_key))


if __name__ == "__main__":
    main()
