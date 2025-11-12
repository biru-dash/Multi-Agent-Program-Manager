"""Non-LLM based metrics evaluation for MIA outputs."""
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
import numpy as np

try:
    from rouge_score import rouge_scorer
    from bert_score import score as bert_score
except ImportError:
    rouge_scorer = None
    bert_score = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class MetricsEvaluator:
    """Traditional metrics-based evaluator for MIA outputs."""
    
    def __init__(self):
        """Initialize metrics evaluator."""
        self.rouge_scorer = rouge_scorer.RougeScorer(
            ['rouge1', 'rouge2', 'rougeL'], use_stemmer=True
        ) if rouge_scorer else None
        
    def evaluate_summary_metrics(
        self,
        generated_summary: str,
        reference_summary: Optional[str] = None,
        source_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate summary using ROUGE and BERTScore metrics."""
        metrics = {}
        
        # ROUGE scores (if reference summary available)
        if reference_summary and self.rouge_scorer:
            rouge_scores = self.rouge_scorer.score(reference_summary, generated_summary)
            metrics['rouge'] = {
                'rouge1': {
                    'precision': rouge_scores['rouge1'].precision,
                    'recall': rouge_scores['rouge1'].recall,
                    'fmeasure': rouge_scores['rouge1'].fmeasure
                },
                'rouge2': {
                    'precision': rouge_scores['rouge2'].precision,
                    'recall': rouge_scores['rouge2'].recall,
                    'fmeasure': rouge_scores['rouge2'].fmeasure
                },
                'rougeL': {
                    'precision': rouge_scores['rougeL'].precision,
                    'recall': rouge_scores['rougeL'].recall,
                    'fmeasure': rouge_scores['rougeL'].fmeasure
                }
            }
            
        # BERTScore (if reference available)
        if reference_summary and bert_score:
            P, R, F1 = bert_score(
                [generated_summary],
                [reference_summary],
                lang='en',
                verbose=False
            )
            metrics['bertscore'] = {
                'precision': float(P[0]),
                'recall': float(R[0]),
                'f1': float(F1[0])
            }
            
        # Coverage metrics (summary vs source)
        if source_text:
            coverage_metrics = self._calculate_coverage_metrics(
                generated_summary,
                source_text
            )
            metrics['coverage'] = coverage_metrics
            
        # Summary statistics
        metrics['statistics'] = {
            'length_chars': len(generated_summary),
            'length_words': len(generated_summary.split()),
            'compression_ratio': len(generated_summary) / len(source_text) if source_text else None
        }
        
        return metrics
        
    def evaluate_extraction_metrics(
        self,
        extracted_items: List[Dict[str, Any]],
        reference_items: Optional[List[Dict[str, Any]]] = None,
        item_type: str = "decisions"
    ) -> Dict[str, Any]:
        """Evaluate extracted items (decisions, actions, risks) metrics."""
        metrics = {}
        
        # Count metrics
        metrics['count'] = len(extracted_items)
        
        # Completeness metrics
        if item_type == "action_items":
            metrics['completeness'] = self._evaluate_action_completeness(extracted_items)
        elif item_type == "risks":
            metrics['completeness'] = self._evaluate_risk_completeness(extracted_items)
        elif item_type == "decisions":
            metrics['completeness'] = self._evaluate_decision_completeness(extracted_items)
            
        # Precision/Recall/F1 (if reference available)
        if reference_items:
            prec_rec_f1 = self._calculate_extraction_prf(
                extracted_items,
                reference_items,
                item_type
            )
            metrics['precision_recall'] = prec_rec_f1
            
        # Diversity metrics
        metrics['diversity'] = self._calculate_diversity_metrics(extracted_items)
        
        return metrics
        
    def _calculate_coverage_metrics(
        self,
        summary: str,
        source: str
    ) -> Dict[str, float]:
        """Calculate how well the summary covers the source content."""
        # Tokenize
        summary_tokens = set(summary.lower().split())
        source_tokens = set(source.lower().split())
        
        # Token overlap
        token_overlap = len(summary_tokens & source_tokens) / len(source_tokens) if source_tokens else 0
        
        # TF-IDF similarity
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([source, summary])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            similarity = 0
            
        return {
            'token_overlap': token_overlap,
            'tfidf_similarity': float(similarity),
            'coverage_score': (token_overlap + similarity) / 2
        }
        
    def _evaluate_action_completeness(
        self,
        actions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Evaluate completeness of action items."""
        if not actions:
            return {'overall': 0}
            
        has_owner = sum(1 for a in actions if a.get('owner'))
        has_timeline = sum(1 for a in actions if a.get('deadline') or a.get('timeline'))
        has_description = sum(1 for a in actions if a.get('action') and len(a.get('action', '')) > 10)
        
        total = len(actions)
        
        return {
            'owner_coverage': has_owner / total,
            'timeline_coverage': has_timeline / total,
            'description_quality': has_description / total,
            'overall': (has_owner + has_timeline + has_description) / (3 * total)
        }
        
    def _evaluate_risk_completeness(
        self,
        risks: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Evaluate completeness of risks."""
        if not risks:
            return {'overall': 0}
            
        has_impact = sum(1 for r in risks if r.get('impact'))
        has_likelihood = sum(1 for r in risks if r.get('likelihood'))
        has_mitigation = sum(1 for r in risks if r.get('mitigation'))
        
        total = len(risks)
        
        return {
            'impact_coverage': has_impact / total,
            'likelihood_coverage': has_likelihood / total,
            'mitigation_coverage': has_mitigation / total,
            'overall': (has_impact + has_likelihood + has_mitigation) / (3 * total)
        }
        
    def _evaluate_decision_completeness(
        self,
        decisions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Evaluate completeness of decisions."""
        if not decisions:
            return {'overall': 0}
            
        has_description = sum(1 for d in decisions if d.get('decision') and len(d.get('decision', '')) > 20)
        has_rationale = sum(1 for d in decisions if d.get('rationale'))
        has_owner = sum(1 for d in decisions if d.get('decision_maker'))
        
        total = len(decisions)
        
        return {
            'description_quality': has_description / total,
            'rationale_coverage': has_rationale / total,
            'ownership_coverage': has_owner / total,
            'overall': (has_description + has_rationale + has_owner) / (3 * total)
        }
        
    def _calculate_extraction_prf(
        self,
        predicted: List[Dict[str, Any]],
        reference: List[Dict[str, Any]],
        item_type: str
    ) -> Dict[str, float]:
        """Calculate precision, recall, and F1 for extracted items."""
        # Simple matching based on key field
        key_field = {
            'decisions': 'decision',
            'action_items': 'action',
            'risks': 'risk'
        }.get(item_type, 'description')
        
        pred_texts = [item.get(key_field, '').lower() for item in predicted]
        ref_texts = [item.get(key_field, '').lower() for item in reference]
        
        # Find matches (simplified - could use more sophisticated matching)
        matches = 0
        for pred in pred_texts:
            for ref in ref_texts:
                if pred and ref and (pred in ref or ref in pred):
                    matches += 1
                    break
                    
        precision = matches / len(predicted) if predicted else 0
        recall = matches / len(reference) if reference else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'matches': matches
        }
        
    def _calculate_diversity_metrics(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate diversity metrics for extracted items."""
        if not items:
            return {'unique_ratio': 0, 'avg_length': 0}
            
        # Get text representations
        texts = []
        for item in items:
            if isinstance(item, dict):
                # Combine relevant text fields
                text_parts = []
                for key in ['decision', 'action', 'risk', 'description']:
                    if key in item and item[key]:
                        text_parts.append(str(item[key]))
                texts.append(' '.join(text_parts))
            else:
                texts.append(str(item))
                
        # Calculate uniqueness
        unique_texts = set(texts)
        unique_ratio = len(unique_texts) / len(texts) if texts else 0
        
        # Average length
        avg_length = sum(len(t) for t in texts) / len(texts) if texts else 0
        
        return {
            'unique_ratio': unique_ratio,
            'avg_length': avg_length,
            'total_items': len(items)
        }
        
    def calculate_aggregate_metrics(
        self,
        all_metrics: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate aggregate metrics across all components."""
        aggregate = {
            'overall_quality': 0,
            'component_scores': {}
        }
        
        # Calculate component scores
        for component, metrics in all_metrics.items():
            if component == 'summary' and 'rouge' in metrics:
                # Use ROUGE-L F1 as summary score
                score = metrics['rouge']['rougeL']['fmeasure']
            elif 'completeness' in metrics:
                # Use overall completeness as extraction score
                score = metrics['completeness'].get('overall', 0)
            else:
                score = 0
                
            aggregate['component_scores'][component] = score
            
        # Overall quality (average of component scores)
        if aggregate['component_scores']:
            aggregate['overall_quality'] = sum(
                aggregate['component_scores'].values()
            ) / len(aggregate['component_scores'])
            
        return aggregate