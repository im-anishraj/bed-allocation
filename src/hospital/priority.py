"""
Patient Priority Scoring Module.

Calculates clinical priority score (0-100) and assigns a priority level
using an if-else / if-elif ladder based on incoming patient attributes.
This is layered on top of the bed allocation system without altering
the underlying greedy bed matching logic.
"""

from typing import Any, Dict, List


def _get_attr(patient: Any, attr_name: str, display_name: str = None, default: Any = False) -> Any:
    """Helper to extract attribute from either a Patient object or dictionary."""
    if hasattr(patient, attr_name):
        val = getattr(patient, attr_name)
        if val is not None:
            return val
    if isinstance(patient, dict):
        if attr_name in patient:
            val = patient[attr_name]
            if val in ("Yes", "True", True, 1):
                return True
            if val in ("No", "False", False, 0):
                return False
            return val
        if display_name and display_name in patient:
            val = patient[display_name]
            if val in ("Yes", "True", True, 1):
                return True
            if val in ("No", "False", False, 0):
                return False
            return val
    return default


def calculate_patient_priority(patient: Any) -> Dict[str, Any]:
    """
    Evaluates patient attributes using an if-else ladder to calculate a priority score (0-100)
    and assign a priority level.

    Evaluated Dimensions:
      - Acuity / Urgency: is_high_acuity, is_end_of_life
      - Infection / Isolation: is_known_covid, is_suspected_covid, is_infection_control
      - Clinical Vulnerability: is_immunosupressed
      - Age / Frailty: age (>= 80, >= 65)
      - Safety Risks: is_falls_risk, needs_visual_supervision, is_dementia_risk

    Priority Tiers:
      - score >= 70 -> HIGH PRIORITY (Immediate Bed Required) (Red)
      - score >= 40 -> MEDIUM PRIORITY (Urgent Admission) (Amber)
      - else -> STANDARD PRIORITY (Routine Admission) (Green)
    """
    score = 0
    factors: List[str] = []

    # 1. Acuity / Urgency Ladder
    is_high_acuity = _get_attr(patient, "is_high_acuity", "High Acuity")
    is_end_of_life = _get_attr(patient, "is_end_of_life", "End of Life Pathway")

    if is_high_acuity and is_end_of_life:
        score += 50
        factors.append("Critical Acuity & End-of-Life Pathway (+50)")
    elif is_high_acuity:
        score += 40
        factors.append("High Clinical Acuity (+40)")
    elif is_end_of_life:
        score += 35
        factors.append("End-of-Life Care Pathway (+35)")
    else:
        pass

    # 2. Infection / Isolation Ladder
    covid_raw = _get_attr(patient, "is_known_covid", "COVID-19 status")
    if covid_raw in ("Red", True, "Yes"):
        is_known_covid = True
    else:
        is_known_covid = False

    suspect_raw = _get_attr(patient, "is_suspected_covid", "COVID-19 status")
    if suspect_raw in ("Amber", True, "Yes"):
        is_suspected_covid = True
    else:
        is_suspected_covid = False

    is_infection_control = _get_attr(
        patient, "is_infection_control", "Infection control (non-COVID)"
    )

    if is_known_covid:
        score += 35
        factors.append("Confirmed COVID-19 Isolation (+35)")
    elif is_suspected_covid:
        score += 25
        factors.append("Suspected COVID-19 Isolation (+25)")
    elif is_infection_control:
        score += 25
        factors.append("Infection Control Barrier Precaution (+25)")
    else:
        pass

    # 3. Clinical Vulnerability Ladder
    is_immunosupressed = _get_attr(patient, "is_immunosupressed", "Immunosupressed")
    if is_immunosupressed:
        score += 30
        factors.append("Immunosuppressed / Protective Isolation (+30)")
    else:
        pass

    # 4. Age / Frailty Ladder
    raw_age = _get_attr(patient, "age", "Age", default=None)
    if raw_age is not None:
        try:
            age = int(raw_age)
            if age >= 80:
                score += 20
                factors.append(f"Geriatric Frailty Risk (Age {age}) (+20)")
            elif age >= 65:
                score += 15
                factors.append(f"Older Adult Vulnerability (Age {age}) (+15)")
            elif age >= 50:
                score += 5
                factors.append(f"Middle-Aged Clinical Monitoring (Age {age}) (+5)")
            else:
                pass
        except (ValueError, TypeError):
            pass

    # 5. Safety Risks Ladder
    is_falls_risk = _get_attr(patient, "is_falls_risk", "Falls risk")
    needs_visual_supervision = _get_attr(
        patient, "needs_visual_supervision", "Visual Supervision"
    )
    is_dementia_risk = _get_attr(patient, "is_dementia_risk", "Confused or wandering")

    if needs_visual_supervision:
        score += 20
        factors.append("Continuous Visual Supervision Required (+20)")
    if is_dementia_risk:
        score += 20
        factors.append("Dementia / Wandering Precaution (+20)")
    if is_falls_risk:
        score += 15
        factors.append("Falls Risk Precaution (+15)")

    # Ensure bounds [0, 100]
    if score > 100:
        score = 100
    elif score < 0:
        score = 0

    # 6. Priority Tier & Ward Routing Ladder (General, Monitor, Critical)
    if score >= 70:
        target_ward = "Critical"
        priority_level = "HIGH PRIORITY (Immediate Bed Required)"
        priority_tier = "HIGH PRIORITY"
        color = "red"
        badge_color = "danger"
    elif score >= 40:
        target_ward = "Monitor"
        priority_level = "MEDIUM PRIORITY (Urgent Admission)"
        priority_tier = "MEDIUM PRIORITY"
        color = "orange"
        badge_color = "warning"
    else:
        target_ward = "General"
        priority_level = "STANDARD PRIORITY (Routine Admission)"
        priority_tier = "STANDARD PRIORITY"
        color = "green"
        badge_color = "success"

    return {
        "score": score,
        "score_str": f"{score} / 100",
        "target_ward": target_ward,
        "ward_destination": f"{target_ward} Ward",
        "priority_level": priority_level,
        "priority_tier": priority_tier,
        "color": color,
        "badge_color": badge_color,
        "factors": factors,
        "factors_summary": ", ".join(factors) if factors else "Routine Clinical Admission (No acute flags)",
    }
