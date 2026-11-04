"""
src/ingestion - Pod A: Multimodal Extraction & Document Parsers
Exports:
- process_pdf: PDF text & visual extraction pipeline
- process_ppt: PowerPoint text & slide visual extraction pipeline
- process_video: Video Whisper transcription & timestamp alignment
- extract_pdf_content: Low-level PDF extractor
- extract_ppt_content: Low-level PPTX extractor
- extract_images_from_pdf, extract_images_from_ppt
- chunk_text: Sliding window chunker
"""

__all__ = [
    "process_pdf",
    "process_ppt",
    "process_video",
    "extract_pdf_content",
    "extract_ppt_content",
    "extract_images_from_pdf",
    "extract_images_from_ppt",
    "chunk_text",
]

from importlib import import_module


_EXPORTS = {
    "chunk_text": "processing.chunker",
    "extract_pdf_content": "ingestion.pdf_parser",
    "extract_ppt_content": "ingestion.ppt_parser",
    "extract_images_from_pdf": "ingestion.pdf_image_extractor",
    "extract_images_from_ppt": "ingestion.ppt_image_extractor",
    "process_pdf": "ingestion.pdf_pipeline",
    "process_ppt": "ingestion.ppt_pipeline",
    "process_video": "ingestion.video_pipeline",
}


def __getattr__(name: str):
    """Load optional models/providers only for explicitly requested pipelines."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{_EXPORTS[name]}"), name)
    globals()[name] = value
    return value
