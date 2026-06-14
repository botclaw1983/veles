from pathlib import Path

from config.settings import settings
from models.document import Document, DocumentFields


def fetch_documents_from_pdf_docs(
    pdf_dir: Path | None = None,
    *,
    existing_paths: set[str] | None = None,
) -> list[Document]:
    """Сканирует папку pdf_docs и создаёт Document для каждого нового PDF."""
    directory = pdf_dir or settings.pdf_docs_dir
    directory.mkdir(parents=True, exist_ok=True)

    known = existing_paths or set()
    documents: list[Document] = []

    for path in sorted(directory.glob("*.pdf")):
        resolved = str(path.resolve())
        if resolved in known:
            continue

        name = path.stem.replace("_", " ")
        documents.append(
            Document(
                fields=DocumentFields(
                    counterparty_name=name,
                    description=path.name,
                ),
                pdf_filename=resolved,
            )
        )

    return documents
