from __future__ import annotations

from pathlib import Path
from typing import Any


def _safe_user_id(user_id: str) -> str:
    text = "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in str(user_id).strip().lower())
    return text.strip("_") or "default"


def _extract_pdf_text(file_path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except Exception:
        return ""
    parts: list[str] = []
    reader = PdfReader(str(file_path))
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _extract_docx_text(file_path: Path) -> str:
    try:
        import docx  # type: ignore[import-not-found]
    except Exception:
        return ""
    document = docx.Document(str(file_path))
    return "\n".join((p.text or "").strip() for p in document.paragraphs).strip()


def _extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(file_path)
    if suffix == ".docx":
        return _extract_docx_text(file_path)
    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    return ""


def save_base_resume(user_id: str, filename: str, content: bytes, root: Path = Path("data/resumes")) -> dict[str, Any]:
    uid = _safe_user_id(user_id)
    user_dir = root / uid
    user_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(filename).suffix.lower() or ".bin"
    source_path = user_dir / f"base_resume{ext}"
    source_path.write_bytes(content)

    text = _extract_text(source_path)
    md_path = user_dir / "base_resume.md"
    if text.strip():
        md_path.write_text(text.strip() + "\n", encoding="utf-8")
        parsed = True
    else:
        # Keep deterministic placeholder; user can manually edit it.
        if not md_path.exists():
            md_path.write_text(
                "# Base Resume\n\nResume text extraction unavailable. Please paste your resume content here.\n",
                encoding="utf-8",
            )
        parsed = False

    return {
        "user_id": uid,
        "source_path": str(source_path),
        "canonical_markdown_path": str(md_path),
        "parsed_ok": parsed,
        "char_count": len(text),
    }
