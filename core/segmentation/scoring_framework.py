<<<<<<< HEAD
"""
Scoring Framework for Segments
Designed by Parikshith - Chapter 1

This module defines how segments should be weighted and scored
for risk assessment. This is the specification that will guide
the final scoring implementation.
"""

from .segmenter import Segment
from .metadata import OriginType


class SegmentScoringFramework:
    """
    Framework for scoring and weighting segments.
    
    This defines the logic for how different segment types
    should be weighted in the overall risk assessment.
    """
    
    # Base weights for different origin types
    # Higher weight = more suspicious
    ORIGIN_WEIGHTS = {
        OriginType.USER: 1.0,          # Baseline
        OriginType.QUOTED: 1.2,         # Quoted content may hide instructions
        OriginType.PASTED: 1.5,        # Pasted content is more suspicious
        OriginType.CODEBLOCK: 1.8,     # Code blocks can hide instructions
        OriginType.SYSTEM: 0.5         # System content is less suspicious
    }
    
    # Risk multipliers based on segment characteristics
    RISK_MULTIPLIERS = {
        'has_encoding': 2.0,           # Encoded content is very suspicious
        'high_entropy': 1.8,           # High entropy suggests obfuscation
        'has_urls': 1.3,               # URLs can be suspicious
        'is_code': 1.5,                # Code is inherently more risky
        'long_segment': 1.2,           # Very long segments may hide attacks
    }
    
    @staticmethod
    def calculate_segment_weight(segment: Segment) -> float:
        """
        Calculate the weight for a segment based on its characteristics.
        
        Args:
            segment: The segment to weight
            
        Returns:
            Weight value (higher = more suspicious)
        """
        metadata = segment.metadata
        base_weight = SegmentScoringFramework.ORIGIN_WEIGHTS.get(
            metadata.origin, 1.0
        )
        
        # Apply multipliers
        weight = base_weight
        
        if metadata.encoding_detected:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS['has_encoding']
        
        if metadata.entropy_score and metadata.entropy_score > 3.5:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS['high_entropy']
        
        if metadata.has_urls:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS['has_urls']
        
        if metadata.is_code:
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS['is_code']
        
        if metadata.length > 500:  # Long segment threshold
            weight *= SegmentScoringFramework.RISK_MULTIPLIERS['long_segment']
        
        # Adjust by confidence
        weight *= metadata.confidence
        
        return weight
    
    @staticmethod
    def get_scoring_priority(segment: Segment) -> int:
        """
        Get priority for scoring order.
        Higher priority segments should be scored first.
        
        Returns:
            Priority value (higher = more priority)
        """
        priority_map = {
            OriginType.CODEBLOCK: 4,
            OriginType.PASTED: 3,
            OriginType.QUOTED: 2,
            OriginType.USER: 1,
            OriginType.SYSTEM: 0
        }
        
        base_priority = priority_map.get(segment.metadata.origin, 1)
        
        # Boost priority for suspicious characteristics
        if segment.metadata.encoding_detected:
            base_priority += 2
        if segment.metadata.entropy_score and segment.metadata.entropy_score > 3.5:
            base_priority += 1
        
        return base_priority
    
    @staticmethod
    def should_review_segment(segment: Segment) -> bool:
        """
        Determine if a segment should be flagged for human review.
        
        Args:
            segment: The segment to check
            
        Returns:
            True if segment should be reviewed
        """
        metadata = segment.metadata
        
        # Always review encoded content
        if metadata.encoding_detected:
            return True
        
        # Review high-entropy pasted content
        if (metadata.origin == OriginType.PASTED and 
            metadata.entropy_score and metadata.entropy_score > 3.5):
            return True
        
        # Review code blocks with suspicious patterns
        if metadata.is_code and metadata.length > 200:
            return True
        
        # Review quoted content with emails (potential injection vector)
        if metadata.origin == OriginType.QUOTED and metadata.has_emails:
            return True
        
=======
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
>>>>>>> 9a6108c25d54356bc677ab0c6fd0d1f8cc80594c
        return False

