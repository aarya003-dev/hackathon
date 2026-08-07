"""Document chunking.

Tries to split source files on function/class (or heading) boundaries first so
a retrieved chunk maps to one coherent unit of code; falls back to plain
character windows with overlap for anything unrecognized. Safe for untrusted
text because no code is ever executed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int


_LANGUAGE_MARKERS: dict[str, re.Pattern[str]] = {
    ".py": re.compile(r"^(def |async def |class )", re.MULTILINE),
    ".js": re.compile(r"^(function |class |export default )", re.MULTILINE),
    ".ts": re.compile(r"^(function |class |export )", re.MULTILINE),
    ".go": re.compile(r"^func ", re.MULTILINE),
    ".md": re.compile(r"^#{1,3} ", re.MULTILINE),
}


def _split_plain(text: str, max_chars: int, overlap: int) -> list[Chunk]:
    """Split by character windows with a small overlap to keep context."""
    text = text.strip()
    if not text:
        return []
    chunks: list[Chunk] = []
    start, index = 0, 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(Chunk(text=text[start:end].strip(), index=index))
        index += 1
        if end == len(text):
            break
        start = max(start, end - overlap)
    return chunks


def _split_at_markers(
    text: str, matches: list[int], max_chars: int, overlap: int
) -> list[Chunk]:
    """Split at marker offsets, sub-splitting any segment that is too long."""
    if not matches:
        return _split_plain(text, max_chars, overlap)
    chunks: list[Chunk] = []
    index = 0
    bounds = matches + [len(text)]
    for i, start in enumerate(matches):
        segment = text[start : bounds[i + 1]].strip()
        if len(segment) > max_chars:
            for sub in _split_plain(segment, max_chars, overlap):
                chunks.append(Chunk(text=sub.text, index=index))
                index += 1
        else:
            chunks.append(Chunk(text=segment, index=index))
            index += 1
    return chunks


def chunk_source(
    text: str,
    file_path: str = "",
    *,
    max_chars: int = 1500,
    overlap: int = 200,
) -> list[Chunk]:
    """Chunk a source document, honoring language boundaries where known."""
    pattern = _LANGUAGE_MARKERS.get(Path(file_path).suffix.lower())
    if pattern is None:
        return _split_plain(text, max_chars, overlap)
    matches = [m.start() for m in pattern.finditer(text)]
    return _split_at_markers(text, matches, max_chars, overlap)


def chunk_text(text: str, *, max_chars: int = 1500, overlap: int = 200) -> list[Chunk]:
    """Chunk plain text (no language boundaries)."""
    return _split_plain(text, max_chars, overlap)
