from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math


def _to_float_rating(x: Any) -> Optional[float]:
    """Normalize ratings/booleans/dicts-with-rating to float in [0,1]."""
    if x is None:
        return None
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float)):
        xf = float(x)
        if math.isnan(xf) or math.isinf(xf):
            return None
        return max(0.0, min(1.0, xf))
    if isinstance(x, dict) and "rating" in x:
        return _to_float_rating(x.get("rating"))
    return None


def _mean(values: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def _avg_question_set(section: Any) -> Optional[float]:
    """Average a dict of questions (each value may be {rating:...} or rating)."""
    if not isinstance(section, dict):
        return None
    return _mean([_to_float_rating(v) for v in section.values()])


def _get(d: Dict[str, Any], path: Tuple[str, ...], default=None):
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _angle_state(data: Dict[str, Any]) -> str:
    """
    Returns: "experience_led" | "expertise_led" | "mixed_or_unclear"
    based on content_angle_m booleans.
    """
    ae = bool(_get(data, ("content_angle_m", "angle_experience"), False))
    ax = bool(_get(data, ("content_angle_m", "angle_expertise"), False))
    if ae and not ax:
        return "experience_led"
    if ax and not ae:
        return "expertise_led"
    return "mixed_or_unclear"


@dataclass
class EEATScores:
    experience: float
    expertise: float
    authoritativeness: float
    trust: float
    overall: float
    weights: Dict[str, float]
    flags: List[str]
    angle_state: str
    is_clear_ymyl: bool


def score_eeat(
    data: Dict[str, Any],
    *,
    enable_angle_penalties: bool = True,
    enable_angle_reweighting: bool = True,
) -> EEATScores:
    flags: List[str] = []

    # --- Detect YMYL severity (supports "tast 2" typo in source) ---
    spectrum = (
        _get(data, ("ymyl", "task 2", "spectrum"))
        or ""
    )
    is_clear_ymyl = isinstance(spectrum, str) and spectrum.strip().lower() == "clear ymyl"

    # --- Angle state ---
    angle_state = _angle_state(data)
    flags.append(f"angle_state:{angle_state}")

    # --- Experience (E) ---
    e_avg = _avg_question_set(data.get("experience_m"))  # 0..1
    E = 100.0 * (e_avg if e_avg is not None else 0.0)

    # --- Expertise (Ex): 60% expertise_m + 40% content_quality_m ---
    ex_avg = _avg_question_set(data.get("expertise_m"))
    cq_avg = _avg_question_set(data.get("content_quality_m"))
    Ex = 100.0 * (
        0.6 * (ex_avg if ex_avg is not None else 0.0)
        + 0.4 * (cq_avg if cq_avg is not None else 0.0)
    )

    # --- Authoritativeness (A): 50% domain proxy + 30% author + 20% reviewer ---
    trust_qratings = _get(data, ("trust_m", "question_ratings"), {}) or {}
    A_domain = _to_float_rating(_get(trust_qratings, ("question_6", "rating"))) or 0.0

    author_present = _get(data, ("author_info_m", "author_present"))
    A_author = _to_float_rating(author_present)
    if A_author is None:
        A_author = _to_float_rating(_get(data, ("author_info_m", "rating"))) or 0.0

    reviewer_present = _get(
        data, ("contributor_author", "reviewer_editor_endorser_present")
    )
    A_reviewer = _to_float_rating(reviewer_present)
    if A_reviewer is None:
        A_reviewer = _to_float_rating(_get(data, ("contributor_author", "rating"))) or 0.0

    A = 100.0 * (0.5 * A_domain + 0.3 * A_author + 0.2 * A_reviewer)

    if A_author == 0.0:
        flags.append("missing_author")
    if A_reviewer == 0.0:
        flags.append("missing_reviewer_editor")

    # --- Trust (T) ---
    t1 = _to_float_rating(_get(trust_qratings, ("question_1", "rating")))
    t2 = _to_float_rating(_get(trust_qratings, ("question_2", "rating")))
    t3 = _to_float_rating(_get(trust_qratings, ("question_3", "rating")))
    T_core = _mean([t1, t2, t3]) or 0.0

    cq = data.get("content_quality_m") or {}
    T_accuracy = _mean(
        [
            _to_float_rating(_get(cq, ("question_3", "rating"))),
            _to_float_rating(_get(cq, ("question_4", "rating"))),
        ]
    ) or 0.0

    exp = data.get("expertise_m") or {}
    T_citations = _to_float_rating(_get(exp, ("question_10", "rating"))) or 0.0
    if T_citations == 0.0:
        flags.append("missing_citations")

    T_transparency = _mean([A_author, A_reviewer]) or 0.0

    T_base = 100.0 * (
        0.6 * T_core + 0.2 * T_accuracy + 0.1 * T_citations + 0.1 * T_transparency
    )

    # YMYL caps
    T = T_base
    if is_clear_ymyl:
        if T_citations == 0.0:
            T = min(T, 75.0)
            flags.append("ymyl_citation_cap_applied")
        if T_transparency == 0.0:
            T = min(T, 70.0)
            flags.append("ymyl_transparency_cap_applied")

    # --- Angle alignment penalties (new) ---
    if enable_angle_penalties:
        if angle_state == "experience_led" and E < 30.0:
            E = max(0.0, E - 10.0)
            flags.append("experience_angle_mismatch_penalty")
        if angle_state == "expertise_led" and Ex < 60.0:
            Ex = max(0.0, Ex - 10.0)
            flags.append("expertise_angle_mismatch_penalty")

    # --- Overall weights (optionally angle-aware) ---
    if not enable_angle_reweighting:
        weights = {"E": 0.10, "Ex": 0.30, "A": 0.20, "T": 0.40} if is_clear_ymyl else \
                  {"E": 0.25, "Ex": 0.25, "A": 0.20, "T": 0.30}
    else:
        if is_clear_ymyl:
            # Trust stays dominant for Clear YMYL
            if angle_state == "experience_led":
                weights = {"E": 0.15, "Ex": 0.25, "A": 0.20, "T": 0.40}
            elif angle_state == "expertise_led":
                weights = {"E": 0.05, "Ex": 0.35, "A": 0.20, "T": 0.40}
            else:
                weights = {"E": 0.10, "Ex": 0.30, "A": 0.20, "T": 0.40}
        else:
            if angle_state == "experience_led":
                weights = {"E": 0.35, "Ex": 0.20, "A": 0.15, "T": 0.30}
            elif angle_state == "expertise_led":
                weights = {"E": 0.15, "Ex": 0.35, "A": 0.20, "T": 0.30}
            else:
                weights = {"E": 0.25, "Ex": 0.25, "A": 0.20, "T": 0.30}

    # --- Final overall score ---
    overall = (
        weights["E"] * E
        + weights["Ex"] * Ex
        + weights["A"] * A
        + weights["T"] * T
    )

    def r(x: float) -> float:
        return round(x, 2)

    return EEATScores(
        experience=r(E),
        expertise=r(Ex),
        authoritativeness=r(A),
        trust=r(T),
        overall=r(overall),
        weights=weights,
        flags=flags,
        angle_state=angle_state,
        is_clear_ymyl=is_clear_ymyl,
    )


# ---- Example usage ----
if __name__ == "__main__":
    import json

    raw = """<PASTE_JSON_HERE>"""
    data = json.loads(raw)

    scores = score_eeat(
        data,
        enable_angle_penalties=True,
        enable_angle_reweighting=True,
    )

    print(scores)
    print({
        "E": scores.experience,
        "Ex": scores.expertise,
        "A": scores.authoritativeness,
        "T": scores.trust,
        "EEAT": scores.overall,
        "weights": scores.weights,
        "angle_state": scores.angle_state,
        "is_clear_ymyl": scores.is_clear_ymyl,
        "flags": scores.flags,
    })