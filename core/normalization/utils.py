# core/normalization/utils.py

"""
Utility functions for:
- Shannon entropy calculation
- Offset mapping between original & normalized text
- Compressed offset map generation
- Character-level diffing (useful for logs/UI)
"""

import math
from typing import List, Tuple, Dict


# -------------------------------------------------------------
# 1. SHANNON ENTROPY
# -------------------------------------------------------------

def shannon_entropy(text: str) -> float:
    """
    Compute Shannon entropy for the input string.
    Higher entropy often indicates obfuscation (e.g., Base64, hex).
    """
    if not text:
        return 0.0

    freq = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1

    length = len(text)
    entropy = 0.0

    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)

    return entropy


# -------------------------------------------------------------
# 2. OFFSET MAP GENERATOR (ROBUST VERSION)
# -------------------------------------------------------------
"""
Creates mapping for each normalized index → original index.

This helps:
- UI to highlight suspicious segments
- Pipeline to trace sanitized text back to origin
"""

def build_offset_map(original: str, normalized: str) -> List[Tuple[int, int]]:
    """
    Returns list of tuples:
        (normalized_index, original_index)

    Strategy:
    - Walk both strings simultaneously
    - When characters differ (e.g., removed invisible chars),
      advance original pointer until a match is found
    - If normalized has extra chars, map them to last known original index
    """

    i, j = 0, 0
    mapping = []
    last_orig = 0

    while j < len(normalized):
        if i < len(original) and original[i] == normalized[j]:
            mapping.append((j, i))
            last_orig = i
            i += 1
            j += 1
        else:
            # Skip removed/altered characters from original
            if i < len(original):
                i += 1
            else:
                # Normalized has extra chars → map to last valid original
                mapping.append((j, last_orig))
                j += 1

    return mapping


# -------------------------------------------------------------
# 3. COMPRESSED OFFSET MAP (PERFORMANCE-ORIENTED)
# -------------------------------------------------------------

def compress_offset_map(offset_map: List[Tuple[int, int]]) -> List[Dict[str, int]]:
    """
    Compresses offset map into runs:

    Example:
    Input:
        [(0,0), (1,1), (2,2), (3,4)]
    Output:
        [
            {"norm_start": 0, "norm_end": 2, "orig_start": 0},
            {"norm_start": 3, "norm_end": 3, "orig_start": 4}
        ]
    """
    if not offset_map:
        return []

    compressed = []
    start_n, start_o = offset_map[0]
    prev_n, prev_o = start_n, start_o

    for n, o in offset_map[1:]:
        # Same continuous run?
        if n == prev_n + 1 and o == prev_o + 1:
            prev_n, prev_o = n, o
            continue

        # Close previous run
        compressed.append({
            "norm_start": start_n,
            "norm_end": prev_n,
            "orig_start": start_o
        })

        # Start a new run
        start_n, start_o = n, o
        prev_n, prev_o = n, o

    # Final run
    compressed.append({
        "norm_start": start_n,
        "norm_end": prev_n,
        "orig_start": start_o
    })

    return compressed


# -------------------------------------------------------------
# 4. CHARACTER-LEVEL DIFF (USEFUL FOR DEBUGGING)
# -------------------------------------------------------------

def char_diff(original: str, normalized: str) -> Dict[str, List[str]]:
    """
    Returns:
    {
        "removed": [...],
        "added": [...],
        "replaced": ["x → y at index i", ...]
    }

    Helps debug what normalization has done.
    """

    removed = []
    added = []
    replaced = []

    o_len = len(original)
    n_len = len(normalized)
    L = min(o_len, n_len)

    # Compare aligned characters
    for i in range(L):
        if original[i] != normalized[i]:
            replaced.append(f"{original[i]} → {normalized[i]} at index {i}")

    # Tail differences
    if o_len > n_len:
        removed.extend(list(original[n_len:]))
    elif n_len > o_len:
        added.extend(list(normalized[o_len:]))

    return {
        "removed": removed,
        "added": added,
        "replaced": replaced
    }
