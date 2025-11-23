"""
Segmentation Logic Implementation
Designed by Parikshith - Chapter 1

This module implements the core segmentation logic that breaks down
user prompts into meaningful segments for risk assessment.
"""

import re
import math
from typing import List, Optional
from dataclasses import dataclass

from .metadata import SegmentMetadata, OriginType


@dataclass
class Segment:
    """Represents a single segment of text"""
    text: str
    metadata: SegmentMetadata
    
    def __str__(self):
        return f"Segment({self.metadata.origin.value}, len={len(self.text)})"


class Segmenter:
    """
    Main segmentation engine that breaks prompts into segments.
    
    Segmentation Strategy:
    1. Identify code blocks (fenced or indented)
    2. Identify quoted content (email snippets, quoted messages)
    3. Identify pasted content (high entropy, unusual patterns)
    4. Split remaining text at sentence boundaries
    5. Tag each segment with its origin
    """
    
    # Code block patterns
    CODE_FENCE_PATTERN = re.compile(
        r'```[\s\S]*?```|`[^`]+`|~~~[\s\S]*?~~~',
        re.MULTILINE
    )
    
    # Quoted content patterns (allows optional leading whitespace)
    QUOTE_PATTERN = re.compile(
        r'^\s*>\s+.*$|^From:.*$|^Subject:.*$|^On.*wrote:.*$',
        re.MULTILINE | re.IGNORECASE
    )
    
    # Multi-line quoted content (for consecutive quote lines, allows indentation)
    QUOTE_BLOCK_PATTERN = re.compile(
        r'(?:^\s*>\s+.*\n?)+',
        re.MULTILINE
    )
    
    # Email patterns
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    # URL patterns
    URL_PATTERN = re.compile(
        r'https?://[^\s]+|www\.[^\s]+',
        re.IGNORECASE
    )
    
    # Sentence boundary pattern (improved)
    SENTENCE_PATTERN = re.compile(
        r'(?<=[.!?])\s+(?=[A-Z])|(?<=\n)\s*(?=[A-Z])',
        re.MULTILINE
    )
    
    def __init__(self):
        """Initialize the segmenter"""
        self.segment_counter = 0
    
    def segment(self, prompt: str) -> List[Segment]:
        """
        Main segmentation method.
        
        Args:
            prompt: The user prompt to segment
            
        Returns:
            List of Segment objects with metadata
        """
        if not prompt or not prompt.strip():
            return []
        
        segments = []
        processed_indices = set()
        
        # Step 1: Extract code blocks first (highest priority)
        code_segments = self._extract_code_blocks(prompt)
        for seg in code_segments:
            segments.append(seg)
            for i in range(seg.metadata.start_index, seg.metadata.end_index):
                processed_indices.add(i)
        
        # Step 2: Extract quoted content
        quote_segments = self._extract_quoted_content(prompt, processed_indices)
        for seg in quote_segments:
            segments.append(seg)
            for i in range(seg.metadata.start_index, seg.metadata.end_index):
                processed_indices.add(i)
        
        # Step 3: Extract pasted content (high entropy, unusual patterns)
        pasted_segments = self._extract_pasted_content(prompt, processed_indices)
        for seg in pasted_segments:
            segments.append(seg)
            for i in range(seg.metadata.start_index, seg.metadata.end_index):
                processed_indices.add(i)
        
        # Step 4: Split remaining text into sentences
        sentence_segments = self._extract_sentences(prompt, processed_indices)
        segments.extend(sentence_segments)
        
        # Sort segments by start index
        segments.sort(key=lambda s: s.metadata.start_index)
        
        return segments
    
    def _extract_code_blocks(self, prompt: str) -> List[Segment]:
        """Extract code blocks from the prompt"""
        segments = []
        
        for match in self.CODE_FENCE_PATTERN.finditer(prompt):
            code_text = match.group(0)
            start_idx = match.start()
            end_idx = match.end()
            
            # Detect language if possible
            language = None
            if code_text.startswith('```'):
                lang_match = re.match(r'```(\w+)', code_text)
                if lang_match:
                    language = lang_match.group(1)
            
            metadata = SegmentMetadata(
                segment_id=f"code_{self._next_id()}",
                origin=OriginType.CODEBLOCK,
                start_index=start_idx,
                end_index=end_idx,
                length=len(code_text),
                is_code=True,
                language=language,
                confidence=0.95
            )
            
            segments.append(Segment(text=code_text, metadata=metadata))
        
        return segments
    
    def _extract_quoted_content(self, prompt: str, processed_indices: set) -> List[Segment]:
        """Extract quoted content (emails, quoted messages)"""
        segments = []
        
        # First, try to match multi-line quote blocks
        for match in self.QUOTE_BLOCK_PATTERN.finditer(prompt):
            start_idx = match.start()
            end_idx = match.end()
            
            # Skip if already processed
            if any(i in processed_indices for i in range(start_idx, end_idx)):
                continue
            
            quote_text = match.group(0).rstrip('\n')
            
            # Check for email indicators
            has_email = bool(self.EMAIL_PATTERN.search(quote_text))
            
            metadata = SegmentMetadata(
                segment_id=f"quote_{self._next_id()}",
                origin=OriginType.QUOTED,
                start_index=start_idx,
                end_index=start_idx + len(quote_text),
                length=len(quote_text),
                has_quotes=True,
                has_emails=has_email,
                confidence=0.85
            )
            
            segments.append(Segment(text=quote_text, metadata=metadata))
            # Mark as processed
            for i in range(start_idx, start_idx + len(quote_text)):
                processed_indices.add(i)
        
        # Then match single-line quote patterns (email headers, etc.)
        for match in self.QUOTE_PATTERN.finditer(prompt):
            start_idx = match.start()
            end_idx = match.end()
            
            # Skip if already processed
            if any(i in processed_indices for i in range(start_idx, end_idx)):
                continue
            
            quote_text = match.group(0)
            
            # Check for email indicators
            has_email = bool(self.EMAIL_PATTERN.search(quote_text))
            
            metadata = SegmentMetadata(
                segment_id=f"quote_{self._next_id()}",
                origin=OriginType.QUOTED,
                start_index=start_idx,
                end_index=end_idx,
                length=len(quote_text),
                has_quotes=True,
                has_emails=has_email,
                confidence=0.85
            )
            
            segments.append(Segment(text=quote_text, metadata=metadata))
        
        return segments
    
    def _extract_pasted_content(self, prompt: str, processed_indices: set) -> List[Segment]:
        """
        Extract content that appears to be pasted from external sources.
        This includes high entropy text, unusual patterns, etc.
        """
        segments = []
        
        # Look for patterns that suggest pasted content:
        # - Long lines without sentence breaks
        # - High entropy regions
        # - Unusual character sequences
        
        lines = prompt.split('\n')
        current_paste_start = None
        current_paste_end = None
        
        for i, line in enumerate(lines):
            line_start = sum(len(l) + 1 for l in lines[:i])  # +1 for newline
            line_end = line_start + len(line)
            
            # Skip if already processed
            if any(idx in processed_indices for idx in range(line_start, line_end)):
                if current_paste_start is not None:
                    # Finalize current paste segment
                    paste_text = prompt[current_paste_start:current_paste_end]
                    if len(paste_text.strip()) > 50:  # Minimum length threshold
                        metadata = SegmentMetadata(
                            segment_id=f"pasted_{self._next_id()}",
                            origin=OriginType.PASTED,
                            start_index=current_paste_start,
                            end_index=current_paste_end,
                            length=len(paste_text),
                            confidence=0.70
                        )
                        segments.append(Segment(text=paste_text, metadata=metadata))
                    current_paste_start = None
                continue
            
            # Heuristics for pasted content
            is_pasted = (
                len(line) > 200 and not re.search(r'[.!?]\s+', line) or  # Very long line
                self._has_high_entropy(line) or  # High entropy
                bool(self.URL_PATTERN.search(line)) and len(line) > 100  # URL in long line
            )
            
            if is_pasted:
                if current_paste_start is None:
                    current_paste_start = line_start
                current_paste_end = line_end
            else:
                if current_paste_start is not None:
                    # Finalize current paste segment
                    paste_text = prompt[current_paste_start:current_paste_end]
                    if len(paste_text.strip()) > 50:
                        metadata = SegmentMetadata(
                            segment_id=f"pasted_{self._next_id()}",
                            origin=OriginType.PASTED,
                            start_index=current_paste_start,
                            end_index=current_paste_end,
                            length=len(paste_text),
                            confidence=0.70
                        )
                        segments.append(Segment(text=paste_text, metadata=metadata))
                    current_paste_start = None
        
        # Handle trailing paste segment
        if current_paste_start is not None:
            paste_text = prompt[current_paste_start:current_paste_end]
            if len(paste_text.strip()) > 50:
                metadata = SegmentMetadata(
                    segment_id=f"pasted_{self._next_id()}",
                    origin=OriginType.PASTED,
                    start_index=current_paste_start,
                    end_index=current_paste_end,
                    length=len(paste_text),
                    confidence=0.70
                )
                segments.append(Segment(text=paste_text, metadata=metadata))
        
        return segments
    
    def _extract_sentences(self, prompt: str, processed_indices: set) -> List[Segment]:
        """Extract sentences from remaining unprocessed text"""
        segments = []
        
        # Find sentence boundaries in unprocessed areas
        sentence_starts = []
        
        # Start from beginning if not processed
        if 0 not in processed_indices:
            sentence_starts.append(0)
        
        # Find sentence boundaries
        for match in self.SENTENCE_PATTERN.finditer(prompt):
            pos = match.end()
            # Only add if this position and the area after it are not processed
            if pos not in processed_indices and pos < len(prompt):
                # Check if the next character area is unprocessed
                if pos not in sentence_starts:
                    sentence_starts.append(pos)
        
        # Also split on newlines if they're not in processed areas
        for i, char in enumerate(prompt):
            if char == '\n' and i not in processed_indices:
                next_pos = i + 1
                if next_pos < len(prompt) and next_pos not in processed_indices:
                    if next_pos not in sentence_starts:
                        sentence_starts.append(next_pos)
        
        sentence_starts = sorted(set(sentence_starts))
        
        # Extract sentences from unprocessed regions
        for i in range(len(sentence_starts)):
            start_idx = sentence_starts[i]
            end_idx = sentence_starts[i + 1] if i + 1 < len(sentence_starts) else len(prompt)
            
            # Skip if any part is already processed
            if any(idx in processed_indices for idx in range(start_idx, end_idx)):
                continue
            
            sentence_text = prompt[start_idx:end_idx].strip()
            if not sentence_text:
                continue
            
            # Check for URLs and emails
            has_urls = bool(self.URL_PATTERN.search(sentence_text))
            has_emails = bool(self.EMAIL_PATTERN.search(sentence_text))
            
            metadata = SegmentMetadata(
                segment_id=f"user_{self._next_id()}",
                origin=OriginType.USER,
                start_index=start_idx,
                end_index=end_idx,
                length=len(sentence_text),
                has_urls=has_urls,
                has_emails=has_emails,
                confidence=0.90
            )
            
            segments.append(Segment(text=sentence_text, metadata=metadata))
        
        return segments
    
    def _get_unprocessed_text(self, prompt: str, processed_indices: set) -> str:
        """Get the portion of text that hasn't been processed yet"""
        unprocessed_chars = []
        for i, char in enumerate(prompt):
            if i not in processed_indices:
                unprocessed_chars.append(char)
        return ''.join(unprocessed_chars)
    
    def _has_high_entropy(self, text: str, threshold: float = 3.5) -> bool:
        """
        Simple entropy check to detect high-entropy content.
        Returns True if entropy is above threshold.
        """
        if len(text) < 10:
            return False
        
        # Calculate character frequency
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate Shannon entropy
        entropy = 0.0
        text_len = len(text)
        for count in char_counts.values():
            probability = count / text_len
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy > threshold
    
    def _next_id(self) -> int:
        """Generate next segment ID"""
        self.segment_counter += 1
        return self.segment_counter

