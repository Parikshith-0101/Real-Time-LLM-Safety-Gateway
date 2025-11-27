# core/normalization/homoglyphs.py

"""
Homoglyph detection module (enhanced version).

Improvements:
- Expanded homoglyph mapping (safe + curated)
- Structured detection output
- Script identification (Latin, Cyrillic, Greek)
- Confusable flag for security scoring
"""

import unicodedata

# Safe + conservative homoglyph mapping used for detection + optional replacement
HOMOGLYPH_MAP = {
    # Fullwidth alphabet
    **{chr(0xFF21 + i): chr(0x41 + i) for i in range(26)},   # Ａ → A
    **{chr(0xFF41 + i): chr(0x61 + i) for i in range(26)},   # ａ → a
    **{chr(0xFF10 + i): chr(0x30 + i) for i in range(10)},   # ０ → 0

    # Cyrillic → Latin (high-risk confusables)
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "і": "i", "ї": "i", "ј": "j", "ѕ": "s",

    # Greek → Latin (visual clones)
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H",
    "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Χ": "X",

    # Mathematical bold/italic/monospace variants (dangerous in obfuscation)
    "𝚊": "a", "𝚋": "b", "𝚌": "c",
    "𝒂": "a", "𝒃": "b", "𝒄": "c",
    "𝓐": "A", "𝓑": "B", "𝓒": "C",
}

# Characters known to be used often in prompt-injection obfuscation
CONFUSABLE_RISK_SET = {
    "а", "е", "о", "р", "с", "х",  # Cyrillic lookalikes
    "Ι", "Ο", "Ρ", "Τ", "Χ",       # Greek lookalikes
}


def get_script(char: str) -> str:
    """
    Identify the Unicode script family (Latin, Cyrillic, Greek, etc.)
    """
    try:
        name = unicodedata.name(char)
    except ValueError:
        return "Unknown"

    if "CYRILLIC" in name:
        return "Cyrillic"
    if "GREEK" in name:
        return "Greek"
    if "LATIN" in name:
        return "Latin"
    if "FULLWIDTH" in name:
        return "Fullwidth"

    return "Other"


def detect_homoglyphs(text: str):
    """
    Detect homoglyph characters with structured output.

    Returns list of dicts:
    {
        "pos": index,
        "char": original character,
        "mapped_to": ASCII equivalent,
        "script": Unicode script family,
        "is_confusable": True/False
    }
    """
    results = []

    for i, ch in enumerate(text):
        if ch in HOMOGLYPH_MAP:
            mapped = HOMOGLYPH_MAP[ch]
            results.append({
                "pos": i,
                "char": ch,
                "mapped_to": mapped,
                "script": get_script(ch),
                "is_confusable": ch in CONFUSABLE_RISK_SET
            })

    return results
