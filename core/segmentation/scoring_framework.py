"""Scoring stubs for Chapter 1.

These are **placeholders only**. Real scoring, prioritisation and
review logic will be implemented in later chapters (ML + rules).
"""

from .segmenter import Segment


class SegmentScoringFramework:
    """Stub scoring framework for Chapter 1.

    The goal in this chapter is to expose a stable interface that
    other components can call, without encoding any real policy
    or ML logic yet.
    """

    @staticmethod
    def calculate_segment_weight(segment: Segment) -> float:
        """Return a constant placeholder weight.

        This keeps behaviour deterministic without encoding
        real risk scoring logic in Chapter 1.
        """
        return 1.0

    @staticmethod
    def get_scoring_priority(segment: Segment) -> int:
        """Return a neutral priority for all segments.

        Kept only so callers can rely on the interface.
        """
        return 0

    @staticmethod
    def should_review_segment(segment: Segment) -> bool:
        """Placeholder: no review logic in Chapter 1.

        Always returns False. Review rules will be added in
        later chapters once scoring and policies are defined.
        """
        return False

