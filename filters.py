"""
filters.py — Product filter and quality scoring logic for dice-tracker.
Scores each result 0-100 based on how well it matches the target spec.
Products scoring below EXCLUDE_THRESHOLD are rejected outright.
"""

EXCLUDE_THRESHOLD = 10  # below this score = auto-excluded

# Keywords that hard-exclude a result
EXCLUDE_KEYWORDS = [
    "glitter", "sparkle", "translucent", "transparent", "see-through",
    "foam", "hollow", "acrylic", "plastic", "sticker pip", "painted pip",
    "gold pips only", "gold number", "gold dot on",
]

# Keywords that signal a good gold body finish
GOLD_BODY_KEYWORDS = [
    "gold", "brass", "bronze", "champagne gold", "polished gold",
    "metallic gold", "antique gold", "deep gold", "solid gold",
]

# Keywords that signal engraved/recessed pips
ENGRAVED_PIP_KEYWORDS = [
    "engraved", "recessed", "inlaid", "etched", "drilled", "indented",
]

# Keywords that signal solid/quality material
QUALITY_MATERIAL_KEYWORDS = [
    "solid metal", "zinc alloy", "brass", "steel", "aluminum", "resin",
    "heavy", "weighted", "substantial",
]


def score_product(title: str, description: str = "", size_mm: float = None,
                  price_usd: float = None) -> dict:
    """
    Score a product result against the dice spec.
    Returns dict with: score (int), flags (list), excluded (bool), reason (str)
    """
    text = (title + " " + description).lower()
    flags = []
    score = 0
    excluded = False
    reason = ""

    # Hard exclusions — check first
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return {
                "score": 0,
                "flags": [f"excluded: {kw}"],
                "excluded": True,
                "reason": f"Excluded keyword: '{kw}'"
            }

    # Size scoring (40 points max)
    if size_mm is not None:
        if size_mm >= 50:
            score += 40
            flags.append(f"size_ok: {size_mm}mm")
        elif size_mm >= 45:
            score += 20
            flags.append(f"size_close: {size_mm}mm")
        elif size_mm >= 40:
            score += 10
            flags.append(f"size_small: {size_mm}mm")
        else:
            score += 0
            flags.append(f"size_too_small: {size_mm}mm")
    else:
        # Try to infer from text
        if "50mm" in text or "2 inch" in text or "2\"" in text or "2in" in text:
            score += 40
            flags.append("size_inferred_50mm")
        elif "45mm" in text or "40mm" in text:
            score += 15
            flags.append("size_inferred_40-45mm")
        elif "jumbo" in text or "large" in text or "oversized" in text:
            score += 10
            flags.append("size_inferred_large")

    # Gold body finish scoring (25 points max)
    gold_hits = [kw for kw in GOLD_BODY_KEYWORDS if kw in text]
    if gold_hits:
        score += 25
        flags.append(f"gold_body: {gold_hits[0]}")
    else:
        flags.append("no_gold_body_detected")

    # Engraved pip scoring (20 points max)
    pip_hits = [kw for kw in ENGRAVED_PIP_KEYWORDS if kw in text]
    if pip_hits:
        score += 20
        flags.append(f"engraved_pips: {pip_hits[0]}")

    # Material quality scoring (15 points max)
    mat_hits = [kw for kw in QUALITY_MATERIAL_KEYWORDS if kw in text]
    if mat_hits:
        score += 15
        flags.append(f"quality_material: {mat_hits[0]}")

    # Set of 3 bonus
    if "set of 3" in text or "3 dice" in text or "3pc" in text or "3 pcs" in text:
        score += 5
        flags.append("set_of_3")
    elif "set of 2" in text or "2 dice" in text or "pair" in text:
        score += 3
        flags.append("set_of_2")

    # Apply exclusion if score too low
    if score < EXCLUDE_THRESHOLD:
        excluded = True
        reason = f"Score {score} below threshold {EXCLUDE_THRESHOLD}"

    return {
        "score": min(score, 100),
        "flags": flags,
        "excluded": excluded,
        "reason": reason,
    }


def infer_size_mm(title: str, description: str = "") -> float | None:
    """Try to extract die size in mm from text."""
    import re
    text = (title + " " + description).lower()
    # Match patterns like "50mm", "50 mm", "2 inch", "2\"", "2in"
    mm = re.search(r'(\d{2,3})\s*mm', text)
    if mm:
        return float(mm.group(1))
    inch = re.search(r'(\d+(?:\.\d+)?)\s*(?:inch|in|")', text)
    if inch:
        return float(inch.group(1)) * 25.4
    return None
