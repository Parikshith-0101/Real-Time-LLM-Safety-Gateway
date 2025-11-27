# core/normalization/normalizer.py

import re
import unicodedata
from typing import Dict, Any
from .homoglyphs import detect_homoglyphs
from .encodings import detect_encoded_payloads
from .utils import shannon_entropy, build_offset_map

# Invisible or zero-width characters to strip
INVISIBLE_RE = re.compile(
    "[" +
    "\u200B"  # ZERO WIDTH SPACE
    "\u200C"  # ZERO WIDTH NON-JOINER
    "\u200D"  # ZERO WIDTH JOINER
    "\uFEFF"  # ZERO WIDTH NO-BREAK SPACE (BOM)
    "\u2060"  # WORD JOINER
    "]"
)

# Control characters except tab/newline
CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


class Normalizer:
    """
    Unicode normalization + metadata extraction.

    Steps:
    - Unicode NFKC/NFC normalization
    - Remove invisible/control characters
    - Detect homoglyphs
    - Detect encoded payloads
    - Entropy calculation
    - Offset mapping for auditability
    """

    def __init__(self, homoglyph_replace: bool = False, nf: str = "NFKC"):
        self.homoglyph_replace = homoglyph_replace
        self.nf = nf

    def normalize(self, text: str) -> Dict[str, Any]:
        original = text

        metadata = {
            "original_length": len(original),
            "invisible_count": 0,
            "control_count": 0,
            "homoglyphs_detected": [],
            "encoded_payloads": [],
            "unicode_nf": self.nf,
            "entropy": None,
        }

        # --- 1. Unicode normalization ---
        norm_text = unicodedata.normalize(self.nf, original)

        # --- 2. Detect invisible + control chars ---
        metadata["invisible_count"] = len(INVISIBLE_RE.findall(norm_text))
        metadata["control_count"] = len(CONTROL_RE.findall(norm_text))

        # Remove invisible/control chars
        norm_text = INVISIBLE_RE.sub("", norm_text)
        norm_text = CONTROL_RE.sub("", norm_text)

        # Replace NO-BREAK SPACE with normal space
        norm_text = norm_text.replace("\u00A0", " ")

        # --- 3. Detect homoglyphs ---
        homoglyphs = detect_homoglyphs(norm_text)
        metadata["homoglyphs_detected"] = homoglyphs

        # Optional replacement with ASCII lookalikes
        if self.homoglyph_replace and homoglyphs:
            chars = list(norm_text)
            for pos, orig_char, mapped_char in homoglyphs:
                chars[pos] = mapped_char
            norm_text = "".join(chars)

        # --- 4. Detect encoded payloads ---
        metadata["encoded_payloads"] = detect_encoded_payloads(norm_text)

        # --- 5. Entropy ---
        metadata["entropy"] = shannon_entropy(norm_text)

        # --- 6. Offset map ---
        offset_map = build_offset_map(original, norm_text)

        return {
            "original_text": original,
            "normalized_text": norm_text,
            "offset_map": offset_map,
            "metadata": metadata,
        }
