"""Deal readiness scoring based on the ten supplied vetting questions."""

from __future__ import annotations

from collections.abc import Mapping


QUESTION_KEYS = (
    "team_execution",
    "owner_sales_reliance",
    "relationship_ownership",
    "financial_quality",
    "revenue_growth",
    "customer_concentration",
    "key_person_risk",
    "legal_cleanliness",
    "asset_ownership",
    "process_transferability",
)

POINTS = {"high": 10, "medium": 5, "low": 0}


def calculate_deal_score(answers_dict: Mapping[str, str]) -> int:
    """Score one complete questionnaire from 0 to 100.

    Each of the ten questions contributes 10, 5, or 0 points for its High,
    Medium, or Low answer. Unknown and incomplete responses are rejected.
    """
    if set(answers_dict) != set(QUESTION_KEYS):
        raise ValueError("A score requires exactly the ten vetting answers")
    try:
        return sum(POINTS[answers_dict[key]] for key in QUESTION_KEYS)
    except KeyError as exc:
        raise ValueError(f"Invalid answer rating: {exc.args[0]}") from exc


def score_band(score: int) -> str:
    """Return the owner-facing readiness band."""
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100")
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def risk_band(score: int) -> str:
    """Return the advisor-facing risk band (inverse of readiness)."""
    return {"High": "Low", "Medium": "Medium", "Low": "High"}[score_band(score)]
