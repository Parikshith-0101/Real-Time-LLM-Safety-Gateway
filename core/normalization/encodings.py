# core/normalization/encodings.py

"""
Enhanced encoding detection module.

Detects:
- Base64 (standard + URL-safe + partial)
- Hexadecimal sequences (≥ 8 chars)
- Percent-encoding sequences
- ROT13 obfuscation
- Caesar shift patterns (1–5)
"""

import re
import base64
from typing import List, Dict, Any


# ----------------------------
# REGEX DEFINITIONS
# ----------------------------

# Standard + URL-safe Base64
BASE64_RE = re.compile(
    r"(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
)
BASE64_URLSAFE_RE = re.compile(
    r"(?:[A-Za-z0-9\-_]{4}){2,}(?:[A-Za-z0-9\-_]{2}==|[A-Za-z0-9\-_]{3}=)?"
)

# Hex sequences (8+ chars), but avoid color codes (#RRGGBB)
HEX_RE = re.compile(
    r"\b(?!#)(?:0x)?[A-Fa-f0-9]{8,}\b"
)

# Percent encoding sequences (%AB%CD%EF)
PCT_SEQ_RE = re.compile(
    r"(?:%[0-9A-Fa-f]{2})+"
)


# ----------------------------
# DETECTION HELPERS
# ----------------------------

def _is_rot13(text: str) -> bool:
    """
    Detect if a string looks like ROT13 text.
    ROT13 encoded text retains alphabetic structure but letters are shifted.
    """
    def rot13(s):
        result = []
        for c in s:
            if "a" <= c <= "z":
                result.append(chr((ord(c) - ord("a") + 13) % 26 + ord("a")))
            elif "A" <= c <= "Z":
                result.append(chr((ord(c) - ord("A") + 13) % 26 + ord("A")))
            else:
                result.append(c)
        return "".join(result)

    decoded = rot13(text)
    # Reasonable heuristic: decoded contains vowels & spaces
    return any(v in decoded for v in "aeiou ") and decoded != text


def _detect_caesar_shift(text: str) -> bool:
    """
    Detect small Caesar shifts (1–5), commonly used in obfuscated prompts.
    Only flags alphabetic sequences.
    """
    alpha = "".join([c for c in text if c.isalpha()])
    if len(alpha) < 6:
        return False  # Avoid tiny false positives

    for shift in range(1, 6):
        decoded = []
        for c in alpha:
            base = "a" if c.islower() else "A"
            decoded.append(chr((ord(c) - ord(base) - shift) % 26 + ord(base)))
        decoded_str = "".join(decoded)

        # Basic test: decoded contains vowels or looks like English-ish text
        if any(v in decoded_str for v in "aeiou"):
            return True

    return False


# ----------------------------
# MAIN DETECTION
# ----------------------------

def detect_encoded_payloads(text: str) -> List[Dict[str, Any]]:
    payloads = []

    # --- Base64 (standard) ---
    for m in BASE64_RE.finditer(text):
        s = m.group(0)
        try:
            if len(s) % 4 == 0:
                base64.b64decode(s, validate=True)
                payloads.append({
                    "type": "base64",
                    "match": s,
                    "span": m.span(),
                    "description": "Standard Base64 payload"
                })
        except Exception:
            pass

    # --- Base64 URL-safe ---
    for m in BASE64_URLSAFE_RE.finditer(text):
        s = m.group(0)
        try:
            if len(s) % 4 == 0:
                base64.urlsafe_b64decode(s + "===")
                payloads.append({
                    "type": "base64_urlsafe",
                    "match": s,
                    "span": m.span(),
                    "description": "URL-safe Base64 payload"
                })
        except Exception:
            pass

    # --- Hex payload ---
    for m in HEX_RE.finditer(text):
        payloads.append({
            "type": "hex",
            "match": m.group(0),
            "span": m.span(),
            "description": "Hexadecimal byte sequence"
        })

    # --- Percent encoding sequences ---
    for m in PCT_SEQ_RE.finditer(text):
        payloads.append({
            "type": "pct-encoding",
            "match": m.group(0),
            "span": m.span(),
            "description": "URL percent-encoded sequence"
        })

    # --- ROT13 detection ---
    if _is_rot13(text):
        payloads.append({
            "type": "rot13",
            "match": None,
            "span": None,
            "description": "ROT13 obfuscated text detected"
        })

    # --- Caesar shift detection ---
    if _detect_caesar_shift(text):
        payloads.append({
            "type": "caesar-shift",
            "match": None,
            "span": None,
            "description": "Possible Caesar-shift obfuscation (1–5)"
        })

    return payloads
