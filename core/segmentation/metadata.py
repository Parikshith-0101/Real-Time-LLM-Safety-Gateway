"""
Segment Metadata Structure
Defines the metadata structure for each segment to support scoring and weighting.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class OriginType(Enum):
<<<<<<< HEAD
    """Origin types for segments"""
    USER = "user"  # Direct user input
    PASTED = "pasted"  # Content pasted from external source
    QUOTED = "quoted"  # Quoted content (emails, messages, etc.)
    CODEBLOCK = "codeblock"  # Code blocks
    SYSTEM = "system"  # System-generated content
=======
    """Origin types for segments (Chapter 1 spec)"""
    USER = "user"                 # Direct user input
    QUOTED = "quoted"             # Quoted content (emails, messages, etc.)
    CODE_BLOCK = "code_block"     # Code blocks delimited by triple backticks
    EXTERNAL_PASTE = "external_paste"  # Long pasted / external content
>>>>>>> 9a6108c25d54356bc677ab0c6fd0d1f8cc80594c


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
<<<<<<< HEAD
    
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
=======

    # Risk indicators / numeric features
    suspicious_keywords: List[str] = None
    entropy_score: Optional[float] = None  # Per-segment entropy
    encoding_detected: Optional[str] = None  # Reserved for later chapters

    # Context
    parent_segment_id: Optional[str] = None  # For nested segments
    confidence: float = 1.0  # Confidence in origin classification

    def __post_init__(self):
        if self.suspicious_keywords is None:
            self.suspicious_keywords = []

    # Convenience aliases to match Chapter 1 spec wording
    @property
    def entropy(self) -> Optional[float]:
        return self.entropy_score

    @entropy.setter
    def entropy(self, value: Optional[float]) -> None:
        self.entropy_score = value

    @property
    def contains_url(self) -> bool:
        return self.has_urls

    @contains_url.setter
    def contains_url(self, value: bool) -> None:
        self.has_urls = value

    @property
    def contains_email(self) -> bool:
        return self.has_emails

    @contains_email.setter
    def contains_email(self, value: bool) -> None:
        self.has_emails = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization"""
        return {
            "segment_id": self.segment_id,
            "origin": self.origin.value,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "length": self.length,
            "token_count": self.token_count,
            "is_code": self.is_code,
            "language": self.language,
            "has_quotes": self.has_quotes,
            "has_urls": self.has_urls,
            "has_emails": self.has_emails,
            "suspicious_keywords": self.suspicious_keywords,
            "entropy_score": self.entropy_score,
            "encoding_detected": self.encoding_detected,
            "parent_segment_id": self.parent_segment_id,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SegmentMetadata":
        """Create metadata from dictionary"""
        data["origin"] = OriginType(data["origin"])
>>>>>>> 9a6108c25d54356bc677ab0c6fd0d1f8cc80594c
        return cls(**data)

