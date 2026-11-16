"""Native slide structures should be searchable without a vision API."""
from importlib import import_module
from pathlib import Path

import pytest
from lxml import etree
from pptx import Presentation
from pptx.util import Inches


def write_fixture(path):
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide.shapes.add_textbox(0, 0, Inches(4), Inches(1)).text = "Newton's second law"
    table = slide.shapes.add_table(2, 2, 0, Inches(1), Inches(4), Inches(1)).table
    for cell, value in zip((table.cell(0, 0), table.cell(0, 1), table.cell(1, 0), table.cell(1, 1)),
                           ("Mass", "Acceleration", "2 kg", "3 m/s^2")):
        cell.text = value
    group = slide.shapes.add_group_shape()
    group.shapes.add_textbox(0, Inches(2), Inches(4), Inches(1)).text = "Grouped force diagram label"
    slide.notes_slide.notes_text_frame.text = "Speaker reminder: distinguish mass from weight."
    textbox = slide.shapes.add_textbox(0, Inches(3), Inches(4), Inches(1))
    paragraph = textbox.text_frame.paragraphs[0]._p
    paragraph.append(etree.fromstring(b'''<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
      <m:r><m:t>a = </m:t></m:r><m:f><m:num><m:r><m:t>F</m:t></m:r></m:num>
      <m:den><m:r><m:t>m</m:t></m:r></m:den></m:f></m:oMath>'''))
    presentation.save(path)


@pytest.mark.parametrize("namespace", ["src.ingestion", "app"])
def test_table_group_notes_and_office_math_survive(namespace, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "backend"))
    path = tmp_path / "native.pptx"
    write_fixture(path)
    units = import_module(f"{namespace}.ingestion.ppt_parser").extract_ppt_content(str(path))
    text = "\n".join(u.text for u in units)
    for expected in ("Newton's second law", "Mass", "2 kg", "3 m/s^2", "Grouped force diagram label",
                     "Speaker reminder", "a = (F)/(m)"):
        assert expected in text, (namespace, expected, text)
    assert all(u.location["slide"] == 1 and u.source_id == path.name for u in units)
