"""Streszczanie transkrypcji przy użyciu LLM (Gemini / Claude)."""

import re
import textwrap
from enum import Enum

from .transcript import (
    BotCheckError,
    VideoMeta,
    get_full_transcript,
    linkify_timestamps,
)


class Provider(Enum):
    GEMINI = "gemini"
    CLAUDE = "claude"
    MANUAL = "manual"

PROMPT = """\
Poniżej znajduje się transkrypcja filmu z YouTube. Na jej podstawie napisz \
streszczenie w języku polskim, w formacie Markdown.

Streszczenie powinno zawierać:
1. **Tytuł** — krótki, opisowy tytuł streszczenia (nagłówek H1); \
nie zaczynaj go od „Streszczenie:"
2. **Główne tezy** — sekcja z kluczowymi punktami filmu (lista)
3. **Streszczenie** — pełne streszczenie filmu, podzielone na sekcje \
odpowiadające rozdziałom (jeśli są). Każda sekcja powinna mieć nagłówek H2 \
z timestampem.
4. **Wnioski** — krótkie podsumowanie najważniejszych wniosków

Wzory matematyczne zapisuj w notacji LaTeX: `$...$` dla wzorów w tekście \
(inline) i `$$...$$` dla wzorów blokowych.

Pisz zwięźle, ale nie pomijaj istotnych informacji. Zachowaj timestampy \
przy kluczowych momentach.

Cały wynik umieść w ramce kodu z oznaczeniem języka markdown, czyli:
```markdown
(tutaj streszczenie)
```

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


def _summarize_gemini(transcript: str, api_key: str) -> str:
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=PROMPT.format(transcript=transcript),
    )
    return response.text


def _summarize_claude(transcript: str, api_key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[
            {"role": "user", "content": PROMPT.format(transcript=transcript)}
        ],
    )
    return message.content[0].text


def _strip_code_fence(text: str) -> str:
    """Usuwa owijającą ramkę ```markdown ... ``` jeśli LLM ją dodał."""
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
        stripped = stripped[first_newline:].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    return stripped


def _strip_summary_prefix(text: str) -> str:
    """Usuwa 'Streszczenie:' z początku tytułu H1 jeśli LLM je dodał."""
    return re.sub(r"^(# )Streszczenie:\s*", r"\1", text, flags=re.MULTILINE)


def postprocess_summary(raw: str, meta: VideoMeta | None = None) -> str:
    """Formatuje surowe streszczenie: wrap + timestampy + nagłówek."""
    text = wrap_markdown(_strip_summary_prefix(_strip_code_fence(raw)))
    if meta:
        text = linkify_timestamps(text, meta.video_id)
        text = meta.format_header() + "\n\n" + text
    return text


def summarize(
    transcript: str,
    api_key: str,
    meta: VideoMeta | None = None,
    provider: Provider = Provider.GEMINI,
) -> str:
    """Wysyła transkrypcję do LLM i zwraca streszczenie w Markdown."""
    if provider == Provider.CLAUDE:
        raw = _summarize_claude(transcript, api_key)
    else:
        raw = _summarize_gemini(transcript, api_key)

    return postprocess_summary(raw, meta)


def main() -> None:
    import os
    import sys

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if not args:
        print("Użycie: streszczenie [--claude] <URL_filmu> [kod_języka]")
        sys.exit(1)

    if "--claude" in flags:
        provider = Provider.CLAUDE
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Błąd: ustaw zmienną ANTHROPIC_API_KEY")
            sys.exit(1)
    else:
        provider = Provider.GEMINI
        api_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not api_key:
            print("Błąd: ustaw zmienną GEMINI_API_KEY lub GOOGLE_API_KEY")
            sys.exit(1)

    url = args[0]
    lang = args[1] if len(args) > 1 else None

    print("Pobieram transkrypcję...", file=sys.stderr)
    try:
        transcript, meta = get_full_transcript(url, lang)
    except BotCheckError as e:
        print(f"Błąd: {e}", file=sys.stderr)
        sys.exit(1)

    label = "Claude" if provider == Provider.CLAUDE else "Gemini"
    print(f"Generuję streszczenie ({label})...", file=sys.stderr)
    print(summarize(transcript, api_key, meta, provider))


if __name__ == "__main__":
    main()
