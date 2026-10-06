from pathlib import Path
from typing import Any
import os

from pypdf import PdfReader

from app.settings import settings

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".json", ".csv", ".js", ".ts", ".tsx",
    ".jsx", ".html", ".css", ".yaml", ".yml", ".pdf", ".env.example",
    ".toml", ".ini", ".xml", ".log", ".sql", ".sh", ".ps1",
}


def _resolve_safe_path(target_path: str) -> Path:
    """Ensure path is within authorized workspace root and prevent directory traversal."""
    root = settings.workspace_root.resolve()
    candidate = Path(target_path)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    # Check that candidate starts with root
    try:
        candidate.relative_to(root)
    except ValueError:
        raise PermissionError(f"Access denied. Path '{target_path}' is outside the authorized workspace directory.")

    return candidate


def search_workspace_files(pattern: str, max_matches: int = 15) -> dict[str, Any]:
    """Search for files in the workspace matching a glob or substring pattern."""
    root = settings.workspace_root
    matches = []
    pattern_lower = pattern.lower().strip()

    try:
        for p in root.rglob("*"):
            if "node_modules" in p.parts or ".git" in p.parts or "__pycache__" in p.parts or ".pytest_cache" in p.parts:
                continue
            if p.is_file():
                rel = str(p.relative_to(root))
                if pattern_lower in p.name.lower() or pattern_lower in rel.lower():
                    matches.append({
                        "filename": p.name,
                        "relative_path": rel,
                        "size_bytes": p.stat().st_size,
                        "extension": p.suffix,
                    })
                    if len(matches) >= max_matches:
                        break
        return {"ok": True, "pattern": pattern, "matches_count": len(matches), "files": matches}
    except Exception as exc:
        return {"ok": False, "pattern": pattern, "error": str(exc)}


def read_workspace_file(file_path: str, max_chars: int = 6000) -> dict[str, Any]:
    """
    Read and extract text from an authorized workspace file or document (including PDF).
    """
    try:
        path = _resolve_safe_path(file_path)
        if not path.exists():
            return {"ok": False, "file_path": file_path, "error": f"File '{file_path}' does not exist."}
        if not path.is_file():
            return {"ok": False, "file_path": file_path, "error": f"Path '{file_path}' is a directory, not a file."}

        ext = path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return {"ok": False, "file_path": file_path, "error": f"File type '{ext}' is not supported for reading."}

        # PDF handling
        if ext == ".pdf":
            reader = PdfReader(str(path))
            pages_text = []
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text:
                    pages_text.append(f"--- Page {idx + 1} ---\n{text}")
                if sum(len(p) for p in pages_text) > max_chars:
                    break
            full_text = "\n\n".join(pages_text)
            truncated = full_text[:max_chars]
            return {
                "ok": True,
                "file_path": str(path.relative_to(settings.workspace_root)),
                "type": "pdf",
                "page_count": len(reader.pages),
                "content": truncated,
                "is_truncated": len(full_text) > max_chars,
            }

        # Text/code/csv/json handling
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        truncated = content[:max_chars]
        return {
            "ok": True,
            "file_path": str(path.relative_to(settings.workspace_root)),
            "type": ext.lstrip("."),
            "size_bytes": path.stat().st_size,
            "content": truncated,
            "is_truncated": len(content) > max_chars,
        }
    except Exception as exc:
        return {"ok": False, "file_path": file_path, "error": str(exc)}


def write_workspace_file(file_path: str, content: str) -> dict[str, Any]:
    """Write or update a file within the authorized workspace."""
    try:
        path = _resolve_safe_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "ok": True,
            "file_path": str(path.relative_to(settings.workspace_root)),
            "size_bytes": len(content.encode("utf-8")),
            "message": f"File '{path.name}' written successfully.",
        }
    except Exception as exc:
        return {"ok": False, "file_path": file_path, "error": str(exc)}
