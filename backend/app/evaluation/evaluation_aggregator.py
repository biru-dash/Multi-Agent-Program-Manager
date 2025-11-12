"""Aggregation logic for combining LLM and human evaluations."""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class EvaluationAggregator:
    """Aggregates LLM, human, and metric-based evaluations."""
    
    def __init__(self):
        """Initialize aggregator with schema."""
        schema_path = Path(__file__).parent.parent / "config" / "evaluation_schema.json"
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
            
    def aggregate_evaluations(
        self,
        llm_eval: Optional[Dict[str, Any]] = None,
        human_eval: Optional[Dict[str, Any]] = None,
        metrics_eval: Optional[Dict[str, Any]] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Aggregate multiple evaluation sources into final scores."""
        # Default weights
        if weights is None:
            weights = {
                'llm': 0.5,
                'human': 0.3,
                'metrics': 0.2
            }
            
        # If human eval exists, adjust weights
        if human_eval:
            weights = {
                'llm': 0.4,
                'human': 0.4,
                'metrics': 0.2
            }
            
        aggregated = {
            'components': {},
            'aggregate_score': 0,
            'sources': [],
            'confidence': 'medium',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Collect all components
        all_components = set()
        if llm_eval and 'evaluations' in llm_eval:
            all_components.update(llm_eval['evaluations'].keys())
        if human_eval and 'evaluations' in human_eval:
            all_components.update(human_eval['evaluations'].keys())
        if metrics_eval:
            all_components.update(metrics_eval.keys())
            
        # Aggregate each component
        for component in all_components:
            component_scores = {}
            component_explanations = {}
            
            # Get LLM scores
            if llm_eval and component in llm_eval.get('evaluations', {}):
                llm_component = llm_eval['evaluations'][component]
                if 'scores' in llm_component:
                    for criterion, score in llm_component['scores'].items():
                        component_scores[f'llm_{criterion}'] = score
                    component_explanations['llm'] = llm_component.get('explanations', {})
                    
            # Get human scores
            if human_eval and component in human_eval.get('evaluations', {}):
                human_component = human_eval['evaluations'][component]
                if 'scores' in human_component:
                    for criterion, score in human_component['scores'].items():
                        component_scores[f'human_{criterion}'] = score
                    component_explanations['human'] = human_component.get('explanations', {})
                    
            # Get metrics scores
            if metrics_eval and component in metrics_eval:
                metrics_component = metrics_eval[component]
                if 'completeness' in metrics_component:
                    component_scores['metrics_completeness'] = metrics_component['completeness'].get('overall', 0) * 10
                if 'rouge' in metrics_component:
                    component_scores['metrics_rouge'] = metrics_component['rouge']['rougeL']['fmeasure'] * 10
                    
            # Calculate final scores for this component
            if component_scores:
                final_scores = self._calculate_final_scores(
                    component_scores,
                    weights,
                    component
                )
                
                aggregated['components'][component] = {
                    'scores': final_scores['scores'],
                    'overall_score': final_scores['overall_score'],
                    'explanations': component_explanations,
                    'raw_scores': component_scores
                }
                
        # Calculate overall aggregate score
        if aggregated['components']:
            total_score = sum(
                comp['overall_score'] 
                for comp in aggregated['components'].values()
            )
            aggregated['aggregate_score'] = round(
                total_score / len(aggregated['components']), 2
            )
            
        # Determine confidence based on agreement
        aggregated['confidence'] = self._calculate_confidence(
            llm_eval,
            human_eval,
            metrics_eval
        )
        
        # Track sources
        if llm_eval:
            aggregated['sources'].append('llm')
        if human_eval:
            aggregated['sources'].append('human')
        if metrics_eval:
            aggregated['sources'].append('metrics')
            
        return aggregated
        
    def _calculate_final_scores(
        self,
        raw_scores: Dict[str, float],
        weights: Dict[str, float],
        component: str
    ) -> Dict[str, Any]:
        """Calculate final weighted scores for a component."""
        # Group scores by criterion
        criteria_scores = {}
        
        for score_key, score_value in raw_scores.items():
            # Extract source and criterion
            parts = score_key.split('_', 1)
            if len(parts) == 2:
                source, criterion = parts
                if criterion not in criteria_scores:
                    criteria_scores[criterion] = {}
                criteria_scores[criterion][source] = score_value
                
        # Calculate weighted score for each criterion
        final_scores = {}
        for criterion, source_scores in criteria_scores.items():
            weighted_sum = 0
            weight_sum = 0
            
            for source, score in source_scores.items():
                if source in weights:
                    weighted_sum += score * weights[source]
                    weight_sum += weights[source]
                    
            if weight_sum > 0:
                final_scores[criterion] = round(weighted_sum / weight_sum, 2)
                
        # Calculate overall score using component weights
        overall_score = 0
        if component in self.schema['components']:
            component_weights = self.schema['components'][component]['weights']
            for criterion, score in final_scores.items():
                if criterion in component_weights:
                    overall_score += score * component_weights[criterion]
                    
        return {
            'scores': final_scores,
            'overall_score': round(overall_score, 2)
        }
        
    def _calculate_confidence(
        self,
        llm_eval: Optional[Dict[str, Any]],
        human_eval: Optional[Dict[str, Any]],
        metrics_eval: Optional[Dict[str, Any]]
    ) -> str:
        """Calculate confidence level based on agreement between sources."""
        if not llm_eval or not human_eval:
            return 'low'
            
        # Compare LLM and human scores
        agreement_scores = []
        
        for component in ['summary', 'decisions', 'action_items', 'risks']:
            llm_score = None
            human_score = None
            
            if (llm_eval and 'evaluations' in llm_eval and 
                component in llm_eval['evaluations'] and
                'overall_score' in llm_eval['evaluations'][component]):
                llm_score = llm_eval['evaluations'][component]['overall_score']
                
            if (human_eval and 'evaluations' in human_eval and
                component in human_eval['evaluations'] and
                'overall_score' in human_eval['evaluations'][component]):
                human_score = human_eval['evaluations'][component]['overall_score']
                
            if llm_score is not None and human_score is not None:
                # Calculate agreement (inverse of difference)
                diff = abs(llm_score - human_score)
                agreement = 1 - (diff / 10)  # Normalize to 0-1
                agreement_scores.append(agreement)
                
        if not agreement_scores:
            return 'low'
            
        avg_agreement = sum(agreement_scores) / len(agreement_scores)
        
        if avg_agreement >= 0.8:
            return 'high'
        elif avg_agreement >= 0.6:
            return 'medium'
        else:
            return 'low'
            
    def generate_improvement_report(
        self,
        aggregated_eval: Dict[str, Any],
        extraction_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a detailed improvement report."""
        report = {
            'summary': '',
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'priority_improvements': []
        }
        
        # Analyze each component
        thresholds = self.schema['scoring']['thresholds']
        
        for component, eval_data in aggregated_eval['components'].items():
            overall_score = eval_data['overall_score']
            
            # Identify strengths and weaknesses
            if overall_score >= thresholds['pass']:
                report['strengths'].append({
                    'component': component,
                    'score': overall_score,
                    'description': f"{component.title()} extraction is performing well"
                })
            else:
                report['weaknesses'].append({
                    'component': component,
                    'score': overall_score,
                    'description': f"{component.title()} extraction needs improvement"
                })
                
                # Add specific recommendations
                for criterion, score in eval_data['scores'].items():
                    if score < thresholds['warning']:
                        recommendation = self._generate_recommendation(
                            component,
                            criterion,
                            score,
                            eval_data.get('explanations', {})
                        )
                        report['recommendations'].append(recommendation)
                        
        # Prioritize improvements
        report['priority_improvements'] = sorted(
            report['recommendations'],
            key=lambda x: x['impact_score'],
            reverse=True
        )[:5]
        
        # Generate summary
        report['summary'] = self._generate_summary(
            aggregated_eval['aggregate_score'],
            len(report['strengths']),
            len(report['weaknesses'])
        )
        
        return report
        
    def _generate_recommendation(
        self,
        component: str,
        criterion: str,
        score: float,
        explanations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate specific improvement recommendation."""
        # Get explanation from evaluations
        llm_explanation = explanations.get('llm', {}).get(criterion, '')
        human_explanation = explanations.get('human', {}).get(criterion, '')
        
        # Generate recommendation based on component and criterion
        recommendations_map = {
            ('summary', 'coverage'): "Ensure summary captures all key discussion points",
            ('summary', 'factuality'): "Verify summary accuracy against transcript",
            ('summary', 'clarity'): "Simplify language and improve structure",
            ('decisions', 'specificity'): "Make decisions more concrete and actionable",
            ('decisions', 'completeness'): "Capture all decisions made in the meeting",
            ('action_items', 'owner'): "Assign clear ownership to each action item",
            ('action_items', 'timeline'): "Add specific deadlines to action items",
            ('risks', 'impact'): "Describe potential impact of each risk clearly",
            ('risks', 'likelihood'): "Assess likelihood/probability of risks"
        }
        
        base_recommendation = recommendations_map.get(
            (component, criterion),
            f"Improve {criterion} for {component}"
        )
        
        return {
            'component': component,
            'criterion': criterion,
            'score': score,
            'recommendation': base_recommendation,
            'details': llm_explanation or human_explanation,
            'impact_score': (10 - score) * 0.1  # Higher impact for lower scores
        }
        
    def _generate_summary(
        self,
        aggregate_score: float,
        num_strengths: int,
        num_weaknesses: int
    ) -> str:
        """Generate executive summary of evaluation."""
        quality_level = self.schema['scoring']['scale']['levels']
        
        # Determine quality tier
        quality = "Average"
        for range_str, level in quality_level.items():
            min_score, max_score = map(int, range_str.split('-'))
            if min_score <= aggregate_score <= max_score:
                quality = level
                break
                
        summary = f"Overall extraction quality: {quality} ({aggregate_score}/10). "
        summary += f"Found {num_strengths} strong areas and {num_weaknesses} areas for improvement. "
        
        if aggregate_score >= 7:
            summary += "The system is performing well overall."
        elif aggregate_score >= 5:
            summary += "The system shows acceptable performance with room for improvement."
        else:
            summary += "Significant improvements are needed for production readiness."
            
        return summary