import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from pptx import Presentation

from app.schemas.content_unit import ContentUnit
from app.processing.chunker import chunk_text



_MATH = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _xml_text(node):
    """Render native text and common Office Math as readable linear notation.

    This is structural extraction, not OCR or certified mathematical conversion.
    Pick AlternateContent's first supported representation to avoid duplicate text.
    """
    tag = node.tag.rsplit("}", 1)[-1]
    children = list(node)
    if tag == "AlternateContent":
        choices = [child for child in children if child.tag.rsplit("}", 1)[-1] == "Choice"]
        return _xml_text(choices[0] if choices else children[-1]) if children else ""
    if tag == "t":
        return node.text or ""
    if tag == "br":
        return "\n"
    def part(name):
        child = next((c for c in children if c.tag == f"{{{_MATH}}}{name}"), None)
        return _xml_text(child) if child is not None else ""
    if node.tag.startswith("{" + _MATH + "}"):
        if tag == "f":
            return f"({part('num')})/({part('den')})"
        if tag in {"sSup", "sSub", "sSubSup"}:
            result = f"({part('e')})"
            if tag in {"sSub", "sSubSup"}:
                result += f"_({part('sub')})"
            if tag in {"sSup", "sSubSup"}:
                result += f"^({part('sup')})"
            return result
        if tag == "rad":
            degree = part('deg')
            return f"root[{degree}]({part('e')})" if degree else f"sqrt({part('e')})"
        if tag == "m":
            rows = [" | ".join(_xml_text(c) for c in row if c.tag.endswith('}e'))
                    for row in children if row.tag.endswith('}mr')]
            return "[" + "; ".join(rows) + "]"
        if tag in {"nary", "limLow", "limUpp", "acc", "bar", "func", "d"}:
            # Do not silently imply a complete reconstruction of complex operators.
            return "[Office Math " + tag + ": " + " ".join(_xml_text(c) for c in children) + "]"
    return "".join(_xml_text(child) for child in children)


def _shape_text(shape):
    if hasattr(shape, "shapes"):
        return "\n".join(filter(None, (_shape_text(child) for child in shape.shapes)))
    if getattr(shape, "has_table", False):
        return "\n".join(" | ".join(_xml_text(cell._tc) for cell in row.cells) for row in shape.table.rows)
    if getattr(shape, "has_text_frame", False):
        return "\n".join(_xml_text(p._p) for p in shape.text_frame.paragraphs).strip()
    return ""


def _extract_ppt_fallback_zip(file_path: str) -> list[tuple[int, str]]:
    """Extract slides text using zipfile XML parsing when python-pptx fails."""
    slides = []
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            slide_names = [n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml", n)]
            slide_names.sort(key=lambda s: int(re.search(r"\d+", s.split("/")[-1]).group()))
            for idx, name in enumerate(slide_names):
                xml_data = z.read(name)
                root = ET.fromstring(xml_data)
                full_text = "\n".join(_xml_text(elem) for elem in root.iter()
                                      if elem.tag == "{http://schemas.openxmlformats.org/drawingml/2006/main}p").strip()
                if full_text:
                    slides.append((idx + 1, full_text))
    except Exception as e:
        print(f"[PPT Parser] Zip XML extraction failed: {e}")
    return slides


def extract_ppt_content(file_path: str) -> list[ContentUnit]:
    source_name = Path(file_path).name
    source_stem = Path(source_name).stem
    content_units = []
    slide_data: list[tuple[int, str]] = []

    try:
        presentation = Presentation(file_path)
        for slide_index, slide in enumerate(presentation.slides, start=1):
            slide_text_parts = [_shape_text(shape) for shape in slide.shapes]
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    slide_text_parts.append("[Speaker notes] " + notes)
            slide_text = "\n".join(part for part in slide_text_parts if part).strip()
            if slide_text:
                slide_data.append((slide_index, slide_text))
    except Exception as exc:
        print(f"[PPT Parser] python-pptx raised '{exc}', falling back to direct XML extraction...")
        slide_data = _extract_ppt_fallback_zip(file_path)

    if not slide_data:
        slide_data = _extract_ppt_fallback_zip(file_path)

    for slide_index, slide_text in slide_data:
        chunks = chunk_text(slide_text)
        for chunk_index, chunk in enumerate(chunks, start=1):
            unit = ContentUnit(
                unit_id=f"{source_stem}_s{slide_index}_c{chunk_index}",
                source_id=source_name,
                source_type="slides",
                location={"slide": slide_index},
                chunk_index=chunk_index,
                content_type="text",
                text=chunk,
                visual_description=None,
                image_path=None,
                topic=None,
                subtopic=None,
                concept_ids=[],
            )
            content_units.append(unit)

    return content_units