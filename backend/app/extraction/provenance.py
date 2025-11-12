"""Provenance tracking for extracted items to show source segments."""
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from app.preprocessing.parser import TranscriptSegment

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceItem:
    """Represents provenance information for an extracted item."""
    source_segment_ids: List[int]  # IDs of source segments
    source_text: List[str]  # Original text snippets
    confidence: float  # Extraction confidence
    extraction_method: str  # How it was extracted (e.g., "llm", "rule_based")
    similarity_scores: List[float]  # Similarity between extraction and source


class ProvenanceTracker:
    """Tracks provenance information for all extractions."""
    
    def __init__(self):
        """Initialize provenance tracker."""
        self.segments: List[TranscriptSegment] = []
        self.segment_embeddings: Optional[List] = None
        self.embedding_model = None
    
    def set_source_segments(self, segments: List[TranscriptSegment], embedding_model=None):
        """Set the source segments for provenance tracking.
        
        Args:
            segments: Source transcript segments
            embedding_model: Model for calculating similarities
        """
        self.segments = segments
        self.embedding_model = embedding_model
        
        # Generate embeddings for similarity calculation
        if embedding_model:
            try:
                segment_texts = [seg.text for seg in segments]
                self.segment_embeddings = embedding_model.encode(segment_texts)
                logger.debug(f"Generated embeddings for {len(segments)} segments")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings: {e}")
                self.segment_embeddings = None
    
    def track_decision(self, decision: Dict[str, Any], extraction_method: str = "llm") -> Dict[str, Any]:
        """Add provenance tracking to a decision.
        
        Args:
            decision: Extracted decision
            extraction_method: Method used for extraction
            
        Returns:
            Decision with provenance information
        """
        decision_text = decision.get('decision', decision.get('text', ''))
        provenance = self._find_provenance(decision_text, extraction_method)
        
        # Add provenance to decision
        decision['provenance'] = {
            'source_segment_ids': provenance.source_segment_ids,
            'source_text': provenance.source_text,
            'similarity_scores': provenance.similarity_scores,
            'extraction_method': provenance.extraction_method
        }
        
        # Update confidence if we have similarity information
        if provenance.similarity_scores:
            avg_similarity = sum(provenance.similarity_scores) / len(provenance.similarity_scores)
            # Boost confidence for high similarity
            if avg_similarity > 0.7:
                decision['confidence'] = min(decision.get('confidence', 0.5) + 0.1, 0.95)
        
        return decision
    
    def track_action(self, action: Dict[str, Any], extraction_method: str = "llm") -> Dict[str, Any]:
        """Add provenance tracking to an action item.
        
        Args:
            action: Extracted action item
            extraction_method: Method used for extraction
            
        Returns:
            Action with provenance information
        """
        action_text = action.get('action', '')
        provenance = self._find_provenance(action_text, extraction_method)
        
        # Add provenance to action
        action['provenance'] = {
            'source_segment_ids': provenance.source_segment_ids,
            'source_text': provenance.source_text,
            'similarity_scores': provenance.similarity_scores,
            'extraction_method': provenance.extraction_method
        }
        
        return action
    
    def track_risk(self, risk: Dict[str, Any], extraction_method: str = "llm") -> Dict[str, Any]:
        """Add provenance tracking to a risk.
        
        Args:
            risk: Extracted risk
            extraction_method: Method used for extraction
            
        Returns:
            Risk with provenance information
        """
        risk_text = risk.get('risk', '')
        provenance = self._find_provenance(risk_text, extraction_method)
        
        # Add provenance to risk
        risk['provenance'] = {
            'source_segment_ids': provenance.source_segment_ids,
            'source_text': provenance.source_text,
            'similarity_scores': provenance.similarity_scores,
            'extraction_method': provenance.extraction_method
        }
        
        return risk
    
    def _find_provenance(self, extracted_text: str, extraction_method: str) -> ProvenanceItem:
        """Find source segments for an extracted item.
        
        Args:
            extracted_text: Text of extracted item
            extraction_method: Method used for extraction
            
        Returns:
            Provenance information
        """
        if not self.segments:
            return ProvenanceItem([], [], 0.0, extraction_method, [])
        
        # Method 1: Semantic similarity (if embeddings available)
        if self.segment_embeddings is not None and self.embedding_model:
            return self._find_semantic_provenance(extracted_text, extraction_method)
        
        # Method 2: Keyword overlap
        return self._find_keyword_provenance(extracted_text, extraction_method)
    
    def _find_semantic_provenance(self, extracted_text: str, extraction_method: str) -> ProvenanceItem:
        """Find provenance using semantic similarity."""
        try:
            # Get embedding for extracted text
            extracted_embedding = self.embedding_model.encode([extracted_text])[0]
            
            # Calculate similarities
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(
                [extracted_embedding],
                self.segment_embeddings
            )[0]
            
            # Find top matching segments
            top_indices = similarities.argsort()[-3:][::-1]  # Top 3 most similar
            
            source_ids = []
            source_texts = []
            scores = []
            
            for idx in top_indices:
                if similarities[idx] > 0.3:  # Minimum similarity threshold
                    source_ids.append(idx)
                    source_texts.append(self.segments[idx].text)
                    scores.append(float(similarities[idx]))
            
            return ProvenanceItem(
                source_segment_ids=source_ids,
                source_text=source_texts,
                confidence=max(scores) if scores else 0.0,
                extraction_method=extraction_method,
                similarity_scores=scores
            )
            
        except Exception as e:
            logger.error(f"Semantic provenance failed: {e}")
            return self._find_keyword_provenance(extracted_text, extraction_method)
    
    def _find_keyword_provenance(self, extracted_text: str, extraction_method: str) -> ProvenanceItem:
        """Find provenance using keyword overlap."""
        extracted_words = set(extracted_text.lower().split())
        
        matches = []
        
        for i, segment in enumerate(self.segments):
            segment_words = set(segment.text.lower().split())
            
            # Calculate Jaccard similarity
            overlap = len(extracted_words & segment_words)
            union = len(extracted_words | segment_words)
            
            if union > 0:
                similarity = overlap / union
                if similarity > 0.1:  # Minimum overlap threshold
                    matches.append((i, segment.text, similarity))
        
        # Sort by similarity and take top matches
        matches.sort(key=lambda x: x[2], reverse=True)
        top_matches = matches[:3]
        
        source_ids = [match[0] for match in top_matches]
        source_texts = [match[1] for match in top_matches]
        scores = [match[2] for match in top_matches]
        
        return ProvenanceItem(
            source_segment_ids=source_ids,
            source_text=source_texts,
            confidence=max(scores) if scores else 0.0,
            extraction_method=extraction_method,
            similarity_scores=scores
        )
    
    def validate_extraction(self, extracted_text: str, threshold: float = 0.5) -> Dict[str, Any]:
        """Validate an extraction against source material.
        
        Args:
            extracted_text: Text to validate
            threshold: Minimum similarity threshold for validation
            
        Returns:
            Validation results
        """
        provenance = self._find_provenance(extracted_text, "validation")
        
        # Check if extraction is well-supported by source
        max_similarity = max(provenance.similarity_scores) if provenance.similarity_scores else 0.0
        
        validation = {
            'is_valid': max_similarity >= threshold,
            'max_similarity': max_similarity,
            'supporting_segments': len(provenance.source_segment_ids),
            'confidence_score': max_similarity,
            'potential_hallucination': max_similarity < 0.3
        }
        
        if validation['potential_hallucination']:
            validation['warning'] = "Low similarity to source - potential hallucination"
        elif validation['is_valid']:
            validation['status'] = "Well-supported by source material"
        else:
            validation['status'] = "Weak support in source material"
        
        return validation
    
    def get_segment_by_id(self, segment_id: int) -> Optional[TranscriptSegment]:
        """Get segment by ID.
        
        Args:
            segment_id: Segment index
            
        Returns:
            Segment if exists, None otherwise
        """
        if 0 <= segment_id < len(self.segments):
            return self.segments[segment_id]
        return None
    
    def get_provenance_summary(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of provenance for a list of items.
        
        Args:
            items: List of extracted items with provenance
            
        Returns:
            Provenance summary statistics
        """
        total_items = len(items)
        items_with_provenance = sum(1 for item in items if 'provenance' in item)
        
        # Calculate average similarity scores
        all_similarities = []
        for item in items:
            if 'provenance' in item:
                similarities = item['provenance'].get('similarity_scores', [])
                all_similarities.extend(similarities)
        
        avg_similarity = sum(all_similarities) / len(all_similarities) if all_similarities else 0.0
        
        # Count potential hallucinations
        potential_hallucinations = sum(
            1 for item in items
            if 'provenance' in item and 
               max(item['provenance'].get('similarity_scores', [0])) < 0.3
        )
        
        return {
            'total_items': total_items,
            'items_with_provenance': items_with_provenance,
            'provenance_coverage': items_with_provenance / total_items if total_items > 0 else 0.0,
            'average_similarity': avg_similarity,
            'potential_hallucinations': potential_hallucinations,
            'hallucination_rate': potential_hallucinations / total_items if total_items > 0 else 0.0
        }