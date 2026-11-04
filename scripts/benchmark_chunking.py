"""Repeatable microbenchmark against the pre-audit chunker; no providers needed.

Run: python -m scripts.benchmark_chunking
This measures chunking only, not end-to-end ingestion or retrieval quality.
"""
import json
from statistics import median
from timeit import repeat

from src.ingestion.processing.chunker import chunk_text


def baseline(text, chunk_size=1200, overlap=200):
    """Original algorithm preserved for the comparison."""
    if not text or not text.strip():
        return []
    text = " ".join(text.split())
    chunks, start, text_length = [], 0, len(text)
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        if end < text_length:
            split_position = max(chunk.rfind("."), chunk.rfind("\n"))
            if split_position > chunk_size * 0.6:
                end = start + split_position + 1
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = max(end - overlap, start + 1)
    return chunks


if __name__ == "__main__":
    text = "a" * 1200
    result = {"workload": "1000 documents, 1200 characters each; 7 repeats", "results": {}}
    for name, function in (("before", baseline), ("after", chunk_text)):
        chunks = function(text)
        durations = repeat(lambda: function(text), number=1000, repeat=7)
        result["results"][name] = {
            "chunks_per_document": len(chunks),
            "indexed_characters_per_document": sum(map(len, chunks)),
            "median_seconds_per_1000_documents": median(durations),
            "all_seconds": durations,
        }
    print(json.dumps(result, indent=2))
