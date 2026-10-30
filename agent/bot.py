import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from helpers.prompt import Prompts

if TYPE_CHECKING:
    from models.models import GuardianSettings, User

log = logging.getLogger(__name__)


@dataclass
class Analysis:
    flagged: bool
    category: str | None
    confidence: float
    description: str
    image_summary: dict[str, Any]
    # True when the AI could not produce a usable answer; the scan is then treated as neutral
    failed: bool = False


CLEAN_DESCRIPTION = "No content matching configured restrictions."


class StubController:
    """Fake classifier results for development, so flows can be tested without Ollama or Gemini.

    Every scan is clean unless a simulation was queued for that user via the /dev endpoints.
    """

    def __init__(self) -> None:
        self._pending: dict[str, dict[str, Any]] = {}

    def simulate(self, user_id: str, category: str, scans: int) -> None:
        self._pending[user_id] = {"category": category, "remaining": scans}

    def clear(self, user_id: str) -> None:
        self._pending.pop(user_id, None)

    def remaining(self, user_id: str) -> int:
        return self._pending.get(user_id, {}).get("remaining", 0)

    def next(self, user_id: str) -> str | None:
        pending = self._pending.get(user_id)
        if not pending:
            return None
        pending["remaining"] -= 1
        if pending["remaining"] <= 0:
            self._pending.pop(user_id)
        return pending["category"]


class ScreenClassifier:
    def __init__(self, ai_to_use: str) -> None:
        self.backend = ai_to_use
        self.prompts = Prompts()
        self.stub = StubController()
        self.engine = None
        if ai_to_use != "stub":
            from .engine import Engine  # imported lazily so the stub works without AI clients configured

            self.engine = Engine(ai_to_use=ai_to_use)
            self.backend = self.engine.backend

    def analyze(
        self,
        image_bytes: bytes,
        user_id: str,
        guardian_settings: "GuardianSettings | None",
        restrictions: list[str],
    ) -> Analysis:
        if self.engine is None:
            return self._stub_analysis(user_id)

        summary = self.engine.describe_image(image_bytes, self.prompts.image_classification_prompt())
        if not summary or not summary.get("summary"):
            log.warning("Image description unusable: %r", summary)
            return self._failed()

        verdict = self.overview(
            image_overview=str(summary.get("detailed_description") or summary["summary"]),
            guardian_settings=guardian_settings,
            guardian_restrictions=restrictions,
        )
        if verdict is None:
            return self._failed(summary)

        flagged = bool(verdict.get("flagged"))
        try:
            confidence = float(verdict.get("confidence") or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        return Analysis(
            flagged=flagged,
            category=verdict.get("category") if flagged else None,
            confidence=confidence,
            description=str(verdict.get("description") or (CLEAN_DESCRIPTION if not flagged else "")),
            image_summary=summary,
        )

    def overview(
        self,
        image_overview: str,
        guardian_settings: "GuardianSettings | None",
        guardian_restrictions: list[str],
    ) -> dict[str, Any] | None:
        """Ask the model whether the described screen matches a restriction. None if unusable."""
        assert self.engine is not None
        allowed = guardian_restrictions or self.default_restrictions
        verdict = self.engine.judge(
            image_overview,
            self.prompts.agent_purpose(
                restricted_categories=allowed,
                strictness=guardian_settings.strictness if guardian_settings else "harsh",
            ),
        )
        if not verdict or not isinstance(verdict.get("flagged"), bool):
            log.warning("Verdict unusable: %r", verdict)
            return None
        # Only accept categories the guardian actually configured
        if verdict["flagged"] and verdict.get("category") not in allowed:
            verdict["category"] = "restricted content"
        return verdict

    def _stub_analysis(self, user_id: str) -> Analysis:
        category = self.stub.next(user_id)
        if category is None:
            return Analysis(
                flagged=False,
                category=None,
                confidence=0.95,
                description=CLEAN_DESCRIPTION,
                image_summary={"summary": "Stubbed scan: an ordinary screen.", "confidence": 0.95},
            )
        return Analysis(
            flagged=True,
            category=category,
            confidence=0.9,
            description=f"Simulated content matching '{category}'.",
            image_summary={"summary": f"Stubbed scan: simulated '{category}' content.", "confidence": 0.9},
        )

    @staticmethod
    def _failed(summary: dict[str, Any] | None = None) -> Analysis:
        return Analysis(
            flagged=False,
            category=None,
            confidence=0.0,
            description="This screen couldn't be analyzed.",
            image_summary=summary or {},
            failed=True,
        )

    @staticmethod
    def breakdown(user: "User", analysis: Analysis, include_name: bool = False) -> str:
        """Text of the report a guardian owner receives about a flagged screen."""
        summary = analysis.image_summary
        confidence = analysis.confidence * 0.5 + float(summary.get("confidence", 0.0) or 0.0) * 0.5
        who = f"{user.name} saw" if include_name else "You saw"
        text = f"{who} content flagged as {analysis.category}."
        if analysis.description:
            text += f" {analysis.description.strip()}"
        if confidence < 0.6:
            text += " (low confidence)"
        return text

    @property
    def default_restrictions(self) -> list[str]:
        return [
            "hate",
            "hate speech",
            "death",
            "gore",
            "graphic content",
            "porn",
            "spam",
            "racism",
            "sexism",
            "potential scam",
            "looksmax",
        ]
