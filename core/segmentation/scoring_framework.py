"""
Scoring Framework for Segments
Designed by Parikshith - Chapter 1/2

This module defines how segments should be weighted and scored
for risk assessment. It is the authoritative scoring logic
used before ML (LightGBM) scoring is applied.
"""

from .segmenter import Segment
from .metadata import OriginType


class SegmentScoringFramework:
    """
    Framework for scoring and weighting segments.

    Defines the logic for how different segment types
    should be weighted in the overall risk assessment.
    """

    # Base weights for different origin types
    # Higher weight = more suspicious
    ORIGIN_WEIGHTS = {
        OriginType.USER: 1.0,               # Baseline
        OriginType.QUOTED: 1.2,             # Quoted content may hide instructions
        OriginType.EXTERNAL_PASTE: 1.5,     # Pasted or long external content
        OriginType.CODEBLOCK: 1.8,          # Code blocks can hide instructions
        OriginType.SYSTEM: 0.5              # System content is less suspicious
    }

    # Risk multipliers based on segment characteristics
    RISK_MULTIPLIERS = {
        "has_encoding": 2.0,     # Encoded content is very suspicious
        "high_entropy": 1.8,     # High entropy suggests obfuscation
        "has_urls": 1.3,         # URLs can be suspicious
        "is_code": 1.5,          # Code is inherently more risky
        "long_segment": 1.2,     # Very long segments may hide attacks
    }

    @staticmethod
    def calculate_segment_weight(segment: Segment) -> float:
        """
        Calculate the weight for a segment based on its characteristics.
        Higher weight = more suspicious.
        """
        metadata = segment.metadata

        base_weight = SegmentScoringFramework.ORIGIN_WEIGHTS.get(
            metadata.origin, 1.0
        )

        weight = base_weight

        # Encoded content (e.g., base64)
        if metadata.encoding_detected:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS["has_encoding"]

        # High entropy (unusual / obfuscated content)
        if metadata.entropy_score and metadata.entropy_score > 3.5:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS["high_entropy"]

        # URLs
        if metadata.has_urls:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS["has_urls"]

        # Code blocks
        if metadata.is_code:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS["is_code"]

        # Very long segment
        if metadata.length > 500:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS["long_segment"]

        # Adjust by confidence
        weight *= metadata.confidence

        return weight

    @staticmethod
    def get_scoring_priority(segment: Segment) -> int:
        """
        Get priority for ordering segments before scoring.
        Higher = processed earlier.
        """
        priority_map = {
            OriginType.CODEBLOCK: 4,
            OriginType.EXTERNAL_PASTE: 3,
            OriginType.QUOTED: 2,
            OriginType.USER: 1,
            OriginType.SYSTEM: 0,
        }

        base_priority = priority_map.get(segment.metadata.origin, 1)

        # Increase priority if suspicious
        if segment.metadata.encoding_detected:
            base_priority += 2

        if segment.metadata.entropy_score and segment.metadata.entropy_score > 3.5:
            base_priority += 1

        return base_priority

    @staticmethod
    def should_review_segment(segment: Segment) -> bool:
        """
        Determine if a segment should be flagged for human review.
        """
        metadata = segment.metadata

        # Always review encoded content
        if metadata.encoding_detected:
            return True

        # High-entropy pasted content
        if (
            metadata.origin == OriginType.EXTERNAL_PASTE
            and metadata.entropy_score
            and metadata.entropy_score > 3.5
        ):
            return True

        # Review large code blocks
        if metadata.is_code and metadata.length > 200:
            return True

        # Quoted emails can contain hidden instructions
        if metadata.origin == OriginType.QUOTED and metadata.has_emails:
            return True

        return False
