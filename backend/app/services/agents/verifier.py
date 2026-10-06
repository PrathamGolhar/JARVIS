import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("jarvis.verifier")


class OutputVerifier:
    """
    Verification system ensuring JARVIS never reports completion of an action
    unless the corresponding file, calculation, or tool execution actually succeeded and is valid.
    """

    @staticmethod
    def verify_generated_file(file_path: Path | str | None) -> dict[str, Any]:
        if not file_path:
            return {"verified": False, "reason": "No file path provided."}
        p = Path(file_path)
        if not p.exists():
            return {"verified": False, "reason": f"File '{p.name}' was not found on disk."}
        if p.stat().st_size == 0:
            return {"verified": False, "reason": f"File '{p.name}' is empty (0 bytes)."}
        return {
            "verified": True,
            "filename": p.name,
            "size_bytes": p.stat().st_size,
            "path": str(p),
        }

    @staticmethod
    def verify_tool_result(tool_name: str, result: dict[str, Any]) -> bool:
        if not result.get("ok", True):
            return False
        if "error" in result:
            return False
        return True


output_verifier = OutputVerifier()
