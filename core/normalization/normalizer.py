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

# Emoji Regex (covers all emoji ranges)
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002500-\U00002BEF"
    "\U00002702-\U000027B0"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\U0001F700-\U0001F77F"
    "]+"
)


class Normalizer:
    """
    Unicode normalization + metadata extraction.

    Enhanced with:
    - Emoji stripping (Option 3)
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
            "emoji_count": 0,
            "homoglyphs_detected": [],
            "encoded_payloads": [],
            "unicode_nf": self.nf,
            "entropy": None,
        }

        # --- 1. Unicode normalization ---
        norm_text = unicodedata.normalize(self.nf, original)

        # --- 2. Invisible & control chars ---
        metadata["invisible_count"] = len(INVISIBLE_RE.findall(norm_text))
        metadata["control_count"] = len(CONTROL_RE.findall(norm_text))

        norm_text = INVISIBLE_RE.sub("", norm_text)
        norm_text = CONTROL_RE.sub("", norm_text)
        norm_text = norm_text.replace("\u00A0", " ")

        # --- 3. Emoji Stripping (Option 3) ---
        emojis_found = EMOJI_RE.findall(norm_text)
        metadata["emoji_count"] = sum(len(e) for e in emojis_found)
        norm_text = EMOJI_RE.sub("", norm_text)

        # --- 4. Homoglyph detection ---
        homoglyphs = detect_homoglyphs(norm_text)
        metadata["homoglyphs_detected"] = homoglyphs

        if self.homoglyph_replace and homoglyphs:
            chars = list(norm_text)
            for pos, orig_char, mapped_char in homoglyphs:
                chars[pos] = mapped_char
            norm_text = "".join(chars)

        # --- 5. Encoded payloads ---
        metadata["encoded_payloads"] = detect_encoded_payloads(norm_text)

        # --- 6. Entropy ---
        metadata["entropy"] = shannon_entropy(norm_text)

        # --- 7. Offset map ---
        offset_map = build_offset_map(original, norm_text)

        return {
            "original_text": original,
            "normalized_text": norm_text,
            "offset_map": offset_map,
            "metadata": metadata,
        }
