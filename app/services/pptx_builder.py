"""PowerPoint builder for Auto-EDA MVP.

Creates a presentation with:
- Title + Executive summary
- Data Overview
- Key Drivers (bullets)
- Anomalies & Caveats (bullets)
- Recommendations (bullets)
- Chart gallery (up to N images)
"""
from __future__ import annotations

from typing import Dict
from pptx import Presentation
from pptx.util import Inches


def build_pptx(narrative: Dict, charts: Dict[str, str], out_path: str, max_charts: int = 8) -> str:
    prs = Presentation()

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "EDA & Findings"
    if len(slide.placeholders) > 1:
        slide.placeholders[1].text = narrative.get("executive_summary", "")

    def add_text(title: str, body: str):
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = title
        s.placeholders[1].text = body

    def add_bullets(title: str, items):
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = title
        tf = s.placeholders[1].text_frame
        tf.clear()
        for b in items or []:
            p = tf.add_paragraph()
            p.text = str(b)
            p.level = 0

    # Narrative sections
    add_text("Data Overview", narrative.get("data_overview", ""))
    add_bullets("Key Drivers", narrative.get("key_drivers", []))
    add_bullets("Anomalies & Caveats", narrative.get("anomalies", []))
    add_bullets("Recommendations", narrative.get("recommendations", []))

    # Chart gallery
    count = 0
    for title, path in list(charts.items())[:max_charts]:
        s = prs.slides.add_slide(prs.slide_layouts[5])  # Title Only
        s.shapes.title.text = title
        try:
            s.shapes.add_picture(path, Inches(1), Inches(1.5), width=Inches(8))
        except Exception:
            # Skip missing or unreadable images
            pass
        count += 1

    prs.save(out_path)
    return out_path
