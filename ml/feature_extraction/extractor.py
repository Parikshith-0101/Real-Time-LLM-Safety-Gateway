import hashlib
import math
import re
from typing import Iterable, List, Sequence

import numpy as np

from core.segmentation import Segment
from core.segmentation.metadata import OriginType


class FeatureExtractor:
    """Feature extractor for hashed n-grams + statistical + boolean features."""

    DEFAULT_NGRAMS: Sequence[int] = (3, 4, 5)
    SEGMENT_TYPE_ORDER: Sequence[OriginType] = (
        OriginType.USER,
        OriginType.QUOTED,
        OriginType.CODE_BLOCK,
        OriginType.EXTERNAL_PASTE,
    )

    SQL_KEYWORDS: Sequence[str] = (
        "select ",
        "insert ",
        "update ",
        "delete ",
        "drop ",
        "union ",
        "information_schema",
        "xp_cmdshell",
        " or 1=1",
        "--",
    )
    PERSONA_PATTERNS: Sequence[str] = (
        "you are now",
        "from now on",
        "pretend to be",
        "act as ",
        "roleplay",
        "persona",
        "dan",
        "jailbreak",
    )
    OVERRIDE_PATTERNS: Sequence[str] = (
        "ignore previous",
        "forget all",
        "disregard ",
        "override ",
        "from this moment",
        "reset your rules",
        "system prompt",
        "ignore the above",
    )
    COMMAND_PATTERNS: Sequence[str] = (
        "rm -rf",
        "chmod ",
        "wget ",
        "curl ",
        "powershell",
        "cmd.exe",
        "bash -i",
        "nc -e",
        "python -c",
    )

    URL_REGEX = re.compile(r"https?://|\bwww\.", re.IGNORECASE)
    EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

    def __init__(self, hash_size: int = 20000, ngrams: Iterable[int] = None) -> None:
        self.hash_size = hash_size
        self.ngrams = tuple(ngrams) if ngrams else self.DEFAULT_NGRAMS

    # ----------------------------------------------------------------------
    # Hashing helpers
    # ----------------------------------------------------------------------
    @staticmethod
    def _hash_ngram(token: str, hash_size: int) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest()
        return int(digest, 16) % hash_size

    def build_char_ngrams(self, text: str) -> np.ndarray:
        vec = np.zeros(self.hash_size, dtype=np.float32)
        if not text:
            return vec

        lowered = text  # no normalization per requirements
        text_len = len(lowered)
        for n in self.ngrams:
            if text_len < n:
                continue
            for idx in range(text_len - n + 1):
                token = lowered[idx : idx + n]
                bucket = self._hash_ngram(token, self.hash_size)
                vec[bucket] += 1.0
        return vec

    # ----------------------------------------------------------------------
    # Statistical features
    # ----------------------------------------------------------------------
    @staticmethod
    def _shannon_entropy(text: str) -> float:
        if not text:
            return 0.0
        counts = {}
        for ch in text:
            counts[ch] = counts.get(ch, 0) + 1
        entropy = 0.0
        length = len(text)
        for count in counts.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        return entropy

    def compute_stats(self, text: str) -> np.ndarray:
        text = text or ""
        length = len(text)
        if length == 0:
            return np.zeros(8, dtype=np.float32)

        whitespace = sum(1 for ch in text if ch.isspace())
        uppercase = sum(1 for ch in text if ch.isupper())
        digits = sum(1 for ch in text if ch.isdigit())
        special = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
        unique_chars = len(set(text))
        tokens = text.split()
        if tokens:
            avg_token_length = sum(len(tok) for tok in tokens) / len(tokens)
            avg_token_length = min(avg_token_length, 20.0)  # clamp extreme values
        else:
            avg_token_length = 0.0

        stats = np.array(
            [
                float(length),
                unique_chars / length,
                uppercase / length,
                digits / length,
                whitespace / length,
                special / length,
                self._shannon_entropy(text),
                avg_token_length,
            ],
            dtype=np.float32,
        )
        return stats

    # ----------------------------------------------------------------------
    # Boolean flag features
    # ----------------------------------------------------------------------
    def compute_boolean_flags(self, text: str) -> np.ndarray:
        lowered = (text or "").lower()
        contains_sql = int(any(keyword in lowered for keyword in self.SQL_KEYWORDS))
        contains_persona = int(any(pattern in lowered for pattern in self.PERSONA_PATTERNS))
        contains_override = int(any(pattern in lowered for pattern in self.OVERRIDE_PATTERNS))
        contains_command = int(any(pattern in lowered for pattern in self.COMMAND_PATTERNS))
        contains_url = int(bool(self.URL_REGEX.search(lowered)))
        contains_email = int(bool(self.EMAIL_REGEX.search(text or "")))

        return np.array(
            [
                contains_sql,
                contains_persona,
                contains_override,
                contains_command,
                contains_url,
                contains_email,
            ],
            dtype=np.float32,
        )

    # ----------------------------------------------------------------------
    # Feature vector assembly
    # ----------------------------------------------------------------------
    def _segment_type_vector(self, origin: OriginType) -> np.ndarray:
        vec = np.zeros(len(self.SEGMENT_TYPE_ORDER), dtype=np.float32)
        if origin in self.SEGMENT_TYPE_ORDER:
            vec[self.SEGMENT_TYPE_ORDER.index(origin)] = 1.0
        return vec

    def build_feature_vector(self, segment: Segment) -> np.ndarray:
        text = segment.text or ""

        hashed = self.build_char_ngrams(text)
        stats = self.compute_stats(text)
        flags = self.compute_boolean_flags(text)
        type_one_hot = self._segment_type_vector(segment.origin_type)

        return np.concatenate([hashed, stats, flags, type_one_hot], dtype=np.float32)

