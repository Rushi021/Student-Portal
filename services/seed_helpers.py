"""Sample files for `flask seed-demo` (valid PDF for materials demo)."""
from __future__ import annotations

from io import BytesIO


def build_sample_pdf_bytes() -> bytes:
    """Return a small valid one-page PDF for local storage under ``uploads/``."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()
