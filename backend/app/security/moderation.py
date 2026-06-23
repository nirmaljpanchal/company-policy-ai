from dataclasses import dataclass
import logging

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    flagged: bool
    categories: list[str]
    scores: dict[str, float]
    error: bool = False


def _get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def moderate(text: str) -> ModerationResult:
    """Call OpenAI moderation API. Returns ModerationResult."""
    settings = get_settings()
    try:
        client = _get_openai_client()
        response = client.moderation.create(
            model=settings.openai_moderation_model,
            input=text
        )

        result = response.results[0]
        flagged = result.flagged

        categories = [cat for cat, score in result.category_scores.items() if score > 0.5]
        scores = {cat: score for cat, score in result.category_scores.items()}

        return ModerationResult(
            flagged=flagged,
            categories=categories,
            scores=scores
        )
    except Exception as e:
        logger.error(f"Moderation API error: {e}")
        return ModerationResult(
            flagged=False,
            categories=[],
            scores={},
            error=True
        )


def check_input(text: str) -> ModerationResult:
    """Moderate user input. On API error, flag as blocked."""
    result = moderate(text)
    if result.error:
        result.flagged = True
    return result


def check_output(text: str) -> ModerationResult:
    """Moderate generated output. On API error, allow (log it)."""
    result = moderate(text)
    if result.error:
        logger.warning("Output moderation failed, allowing generation to pass")
        result.flagged = False
    return result
