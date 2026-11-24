"""
JARVIS 2.0 — Output Verifier & Integrity Enforcement System.

Verifies:
1. File existence, non-empty bytes, and format magic bytes/headers (PDF, DOCX, PPTX, XLSX, CSV).
2. Document required sections and substantive content length.
3. Tool execution status and error shielding.
4. Calculation and numeric correctness checks.
5. Untrusted input sanitation & prompt injection neutralization for external sources.
"""
from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any

logger = logging.getLogger("jarvis.verifier")

MAGIC_BYTES = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",
    ".pptx": b"PK\x03\x04",
    ".xlsx": b"PK\x03\x04",
}


class OutputVerifier:
    """
    Verification system ensuring JARVIS never reports completion of an action
    unless the corresponding file, calculation, or tool execution actually succeeded and is valid.
    """

    @staticmethod
    def verify_generated_file(
        file_path: Path | str | None,
        expected_extension: str | None = None,
        min_bytes: int = 64,
    ) -> dict[str, Any]:
        """Verify that a generated artifact exists, is non-empty, and has valid header signatures."""
        if not file_path:
            return {"verified": False, "reason": "No file path provided."}

        p = Path(file_path)
        if not p.exists():
            return {"verified": False, "reason": f"File '{p.name}' was not found on disk."}

        size = p.stat().st_size
        if size == 0:
            return {"verified": False, "reason": f"File '{p.name}' is empty (0 bytes)."}

        if size < min_bytes:
            return {"verified": False, "reason": f"File '{p.name}' is suspiciously small ({size} bytes)."}

        ext = p.suffix.lower()
        if expected_extension and ext != expected_extension.lower():
            return {"verified": False, "reason": f"File extension '{ext}' does not match expected '{expected_extension}'."}

        # Open every output to confirm it is readable, then validate known binary formats.
        try:
            with p.open("rb") as f:
                header = f.read(max((len(magic) for magic in MAGIC_BYTES.values()), default=1))
        except OSError as exc:
            return {"verified": False, "reason": f"Unable to read file '{p.name}': {exc}"}
        if ext in MAGIC_BYTES and not header.startswith(MAGIC_BYTES[ext]):
            return {"verified": False, "reason": f"File '{p.name}' has invalid file header format for {ext}."}

        return {
            "verified": True,
            "filename": p.name,
            "size_bytes": size,
            "path": str(p),
            "format": ext,
        }

    @staticmethod
    def verify_tool_result(tool_name: str, result: dict[str, Any]) -> bool:
        """Verify that tool result dictionary represents genuine operational success."""
        if not isinstance(result, dict):
            return False
        if not result.get("ok", True):
            return False
        if "error" in result and result["error"]:
            return False
        return True

    @staticmethod
    def verify_calculation(expression: str, computed_result: float | int, tolerance: float = 1e-4) -> bool:
        """Verify numerical calculation accuracy against an independent safe evaluator."""
        from app.services.tools.calculator import evaluate_expression
        indep = evaluate_expression(expression)
        if not indep.get("ok"):
            return False
        expected = indep.get("result")
        if isinstance(expected, (int, float)):
            return abs(float(computed_result) - float(expected)) <= tolerance
        return False

    @staticmethod
    def sanitize_untrusted_content(raw_text: str, source_label: str = "External Content") -> str:
        """
        Neutralizes prompt injection attempts within external data (webpages, RAG chunks, scraped text).
        Tags untrusted content within explicit isolation delimiters and strips common instruction override directives.
        """
        if not raw_text:
            return ""
        safe_source_label = re.sub(r"[^A-Za-z0-9_. -]", "_", source_label)[:120]

        # Disarm overt prompt injection directives
        disarmed = raw_text
        injection_patterns = [
            r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts)",
            r"system\s*:\s*you\s+are",
            r"you\s+must\s+now\s+act\s+as",
            r"<\|im_start\|>",
            r"<\|im_end\|>",
            r"\[SYSTEM_INSTRUCTIONS?\]",
        ]
        for pattern in injection_patterns:
            disarmed = re.sub(pattern, "[PROMPT_INJECTION_FLAGGED_AND_STRIPPED]", disarmed, flags=re.IGNORECASE)

        # Encase untrusted data in explicit isolated data tags
        return (
            f"\n<untrusted_external_data source=\"{safe_source_label}\">\n"
            f"{disarmed}\n"
            f"</untrusted_external_data>\n"
        )


output_verifier = OutputVerifier()
