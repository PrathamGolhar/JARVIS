import json
import logging
from typing import Literal

from app.schemas import CodeAnalysisResponse
from app.services.ai.factory import get_ai_provider

logger = logging.getLogger("jarvis.coding_assistant")


def analyze_code_task(
    code: str,
    language: str = "python",
    task: Literal["explain", "debug", "refactor", "generate_tests", "optimize"] = "explain",
) -> CodeAnalysisResponse:
    """
    Perform deep technical code analysis, bug fixing, refactoring, or test generation.
    """
    provider = get_ai_provider()

    system_prompt = (
        f"You are JARVIS Elite Software Engineer and Systems Architect.\n"
        f"Task: {task.upper()} the user's {language} code.\n"
        "Return ONLY JSON matching this format:\n"
        "{\n"
        '  "analysis": "Clear, precise technical explanation...",\n'
        '  "fixedOrImprovedCode": "The corrected/improved code block",\n'
        '  "testCode": "Comprehensive unit tests verifying correctness",\n'
        '  "complexityScore": "O(N) Time, O(1) Space"\n'
        "}"
    )

    user_prompt = f"Language: {language}\n\nCode:\n```{language}\n{code[:8000]}\n```"

    try:
        res = provider.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )

        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        data = json.loads(content.strip())
        if not isinstance(data, dict):
            raise ValueError("The provider response was not a JSON object.")
        analysis = data.get("analysis")
        if not isinstance(analysis, str) or not analysis.strip():
            raise ValueError("The provider response did not contain an analysis.")
        fixed_code = data.get("fixedOrImprovedCode", "")
        test_code = data.get("testCode", "")
        if task in {"debug", "refactor", "optimize"} and (
            not isinstance(fixed_code, str) or not fixed_code.strip()
        ):
            raise ValueError(f"The provider response did not include code for task '{task}'.")
        if task == "generate_tests" and (
            not isinstance(test_code, str) or not test_code.strip()
        ):
            raise ValueError("The provider response did not include generated tests.")
        return CodeAnalysisResponse(
            analysis=analysis,
            fixedOrImprovedCode=fixed_code if isinstance(fixed_code, str) else "",
            testCode=test_code if isinstance(test_code, str) else "",
            complexityScore=data.get("complexityScore", ""),
        )
    except Exception as exc:
        logger.warning("Code assistant analysis failed: %s", exc)
        raise RuntimeError("Code analysis failed; no analysis or test result was generated.") from exc
