"""
合同 PDF 批量入库到 rag.documents。
"""

import sys
from pathlib import Path

from PyPDF2 import PdfReader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import SILICONFLOW_API_KEY
from app.db.database import init_db, SessionLocal
from app.db.models import Document
from app.services.embedding import get_embedding


# ============================================
# region 导入
# ============================================
def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts).strip()


def ingest_folder(folder: Path, collection: str = "contracts") -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        for path in folder.glob("*.pdf"):
            content = extract_text(path)
            if not content:
                continue
            embedding = get_embedding(content) if SILICONFLOW_API_KEY else None
            doc = Document(
                collection=collection,
                source_id=None,
                content=content,
                doc_metadata={"title": path.name},
                embedding=embedding,
            )
            db.add(doc)
            inserted += 1
        db.commit()
    finally:
        db.close()
    return inserted
# endregion
# ============================================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--collection", default="contracts")
    args = parser.parse_args()

    count = ingest_folder(Path(args.folder), collection=args.collection)
    print(f"Inserted: {count}")
