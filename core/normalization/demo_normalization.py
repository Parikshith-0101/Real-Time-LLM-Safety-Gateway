# core/normalization/demo_normalization.py

"""
Demo script for the Normalizer module (Chapter 2).

Run using:
    python core/normalization/demo_normalization.py

Shows:
- Emoji stripping
- Homoglyph detection
- Encoding detection (Base64, hex, pct-encoding, ROT13, Caesar shift)
- Metadata summary
- Offset map verification
- Character diff
"""

from .normalizer import Normalizer
from .utils import char_diff, compress_offset_map


SAMPLES = [
    "Hello\u200B World",  # Invisible char
    "Ｐｌｅａｓｅ Ｒｅａｄ Ｔｈｉｓ",  # Fullwidth homoglyphs
    "Here is base64: SGVsbG8gd29ybGQ=",  # Base64
    "Hex payload: 4A4B4C4D4E4F50",  # Hex
    "Encoded URL: %48%65%6C%6C%6F%21",  # % encoding
    "Emoji test 😊🔥🚀",  # Emoji stripping
    "ROT13: Gur Dhvpx Oebja Qbt",  # ROT13
    "Caesar shift: Ifmmp",  # Shift of +1
    "Cyrillic homoglyph: аpple",  # Cyrillic 'a'
]


def print_section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def run_demo():
    normalizer = Normalizer(homoglyph_replace=False)

    for text in SAMPLES:
        print_section(f"INPUT: {text}")

        out = normalizer.normalize(text)

        print("Normalized:")
        print("  ", out["normalized_text"])

        print("\nMetadata:")
        for k, v in out["metadata"].items():
            print(f"  {k}: {v}")

        print("\nOffset Map (compressed):")
        compressed = compress_offset_map(out["offset_map"])
        print(" ", compressed)

        print("\nCharacter Diff:")
        diff = char_diff(out["original_text"], out["normalized_text"])
        print(" ", diff)

        print("\n" + "-" * 60)


if __name__ == "__main__":
    run_demo()
