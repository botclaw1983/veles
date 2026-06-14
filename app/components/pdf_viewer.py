from pathlib import Path

import fitz
import streamlit as st


def render_pdf(pdf_path: str | Path, *, height: int = 900) -> None:
    """Просмотр PDF: страницы рендерятся в изображения (надёжно в Streamlit)."""
    path = Path(pdf_path)
    doc = fitz.open(path)
    try:
        page_count = doc.page_count
        matrix = fitz.Matrix(2.0, 2.0)

        with st.container(height=height):
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                st.image(pix.tobytes("png"), use_container_width=True)
                if page_count > 1:
                    st.caption(f"Страница {page_num + 1} из {page_count}")
    finally:
        doc.close()
