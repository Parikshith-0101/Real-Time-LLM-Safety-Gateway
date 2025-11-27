"""
Segmentation and Origin Tagging Module
Designed by Parikshith for LLM Safety Gateway

This module handles breaking down user prompts into segments
and tagging them with their origin for proper risk assessment.
"""

from .segmenter import Segmenter, Segment, OriginType
from .metadata import SegmentMetadata
from .scoring_framework import SegmentScoringFramework

__all__ = ['Segmenter', 'Segment', 'OriginType', 'SegmentMetadata', 'SegmentScoringFramework']

