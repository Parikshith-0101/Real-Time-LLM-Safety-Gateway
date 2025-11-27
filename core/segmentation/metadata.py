"""
Segment Metadata Structure
Defines the metadata structure for each segment to support scoring and weighting.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class OriginType(Enum):
    """Origin types for segments"""
    USER = "user"  # Direct user input
    PASTED = "pasted"  # Content pasted from external source
    QUOTED = "quoted"  # Quoted content (emails, messages, etc.)
    CODEBLOCK = "codeblock"  # Code blocks
    SYSTEM = "system"  # System-generated content


@dataclass
class SegmentMetadata:
    """
    Metadata structure for each segment.
    This will be used for scoring, weighting, and risk assessment.
    """
    segment_id: str
    origin: OriginType
    start_index: int
    end_index: int
    length: int
    token_count: Optional[int] = None
    
    # Content characteristics
    is_code: bool = False
    language: Optional[str] = None  # For code blocks
    has_quotes: bool = False
    has_urls: bool = False
    has_emails: bool = False
    
    # Risk indicators
    suspicious_keywords: List[str] = None
    entropy_score: Optional[float] = None
    encoding_detected: Optional[str] = None  # base64, hex, etc.
    
    # Context
    parent_segment_id: Optional[str] = None  # For nested segments
    confidence: float = 1.0  # Confidence in origin classification
    
    def __post_init__(self):
        if self.suspicious_keywords is None:
            self.suspicious_keywords = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization"""
        return {
            'segment_id': self.segment_id,
            'origin': self.origin.value,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'length': self.length,
            'token_count': self.token_count,
            'is_code': self.is_code,
            'language': self.language,
            'has_quotes': self.has_quotes,
            'has_urls': self.has_urls,
            'has_emails': self.has_emails,
            'suspicious_keywords': self.suspicious_keywords,
            'entropy_score': self.entropy_score,
            'encoding_detected': self.encoding_detected,
            'parent_segment_id': self.parent_segment_id,
            'confidence': self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SegmentMetadata':
        """Create metadata from dictionary"""
        data['origin'] = OriginType(data['origin'])
        return cls(**data)

