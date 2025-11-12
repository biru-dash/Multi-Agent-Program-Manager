"""LangChain-based evaluation chains for Meeting Intelligence Agent outputs."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from langchain_core.prompts import PromptTemplate
try:
    from langchain.chains import LLMChain
except ImportError:
    from langchain_classic.chains import LLMChain
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI
try:
    from langchain.callbacks.tracers import LangChainTracer
except ImportError:
    try:
        from langchain_community.callbacks.tracers import LangChainTracer
    except ImportError:
        LangChainTracer = None

from langsmith import Client

from app.config.settings import settings
from app.models.adapter import get_model_adapter
from app.evaluation.model_adapter import get_evaluation_model_adapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load evaluation schema
schema_path = Path(__file__).parent.parent / "config" / "evaluation_schema.json"
with open(schema_path, 'r') as f:
    EVALUATION_SCHEMA = json.load(f)

# LangSmith client for tracing
langsmith_client = None
tracer = None
if settings.langsmith_api_key and LangChainTracer:
    try:
        langsmith_client = Client(api_key=settings.langsmith_api_key)
        tracer = LangChainTracer(
            project_name=settings.langsmith_project_name or "mia-evaluations",
            client=langsmith_client
        )
    except Exception as e:
        logger.warning(f"Failed to initialize LangSmith tracer: {e}")
        tracer = None


class EvaluationChain:
    """Automated evaluation chain for MIA outputs using LangChain."""
    
    def __init__(self, cache_enabled: bool = True):
        """Initialize evaluation chain with configured model."""
        self.cache_enabled = cache_enabled
        self.schema = EVALUATION_SCHEMA
        
        # Initialize LLM for evaluation using the model adapter
        self.model_adapter = get_evaluation_model_adapter()
        self.llm = self.model_adapter.get_llm()
        self.judge_model = f"{settings.evaluation_model_provider}:{settings.evaluation_model_name}"
        
        logger.info(f"Initialized evaluation chain with {settings.evaluation_model_provider} model")
        
        # Create evaluation prompts
        self._create_prompts()
        
    def _create_prompts(self):
        """Create evaluation prompts for each component."""
        self.prompts = {}
        
        # Summary evaluation prompt
        self.prompts['summary'] = PromptTemplate(
            input_variables=["transcript", "summary", "criteria"],
            template="""You are an expert evaluator for meeting summaries. 
Given the original transcript and a generated summary, evaluate it based on these criteria:

{criteria}

Original Transcript:
{transcript}

Generated Summary:
{summary}

For each criterion, provide:
1. A score from 0-10
2. A brief explanation of your score (1-2 sentences)

IMPORTANT: Return ONLY a valid JSON object with this exact structure:
{{
    "scores": {{
        "coverage": 7,
        "factuality": 8,
        "clarity": 6
    }},
    "explanations": {{
        "coverage": "Brief explanation here",
        "factuality": "Brief explanation here", 
        "clarity": "Brief explanation here"
    }},
    "overall_score": 7.0
}}
"""
        )
        
        # Decisions evaluation prompt  
        self.prompts['decisions'] = PromptTemplate(
            input_variables=["transcript", "decisions", "criteria"],
            template="""You are an expert evaluator for meeting decisions extraction.
Given the original transcript and extracted decisions, evaluate them based on these criteria:

{criteria}

Original Transcript:
{transcript}

Extracted Decisions:
{decisions}

For each criterion, provide:
1. A score from 0-10
2. A brief explanation of your score (1-2 sentences)

Return your evaluation as a JSON object with this structure:
{{
    "scores": {{
        "specificity": <score>,
        "completeness": <score>,
        "clarity": <score>
    }},
    "explanations": {{
        "specificity": "<explanation>",
        "completeness": "<explanation>",
        "clarity": "<explanation>"
    }},
    "overall_score": <weighted average>
}}
"""
        )
        
        # Action items evaluation prompt
        self.prompts['action_items'] = PromptTemplate(
            input_variables=["transcript", "action_items", "criteria"],
            template="""You are an expert evaluator for meeting action items.
Given the original transcript and extracted action items, evaluate them based on these criteria:

{criteria}

Original Transcript:
{transcript}

Extracted Action Items:
{action_items}

For each criterion, provide:
1. A score from 0-10
2. A brief explanation of your score (1-2 sentences)

Return your evaluation as a JSON object with this structure:
{{
    "scores": {{
        "owner": <score>,
        "timeline": <score>,
        "clarity": <score>,
        "priority": <score>
    }},
    "explanations": {{
        "owner": "<explanation>",
        "timeline": "<explanation>",
        "clarity": "<explanation>",
        "priority": "<explanation>"
    }},
    "overall_score": <weighted average>
}}
"""
        )
        
        # Risks evaluation prompt
        self.prompts['risks'] = PromptTemplate(
            input_variables=["transcript", "risks", "criteria"],
            template="""You are an expert evaluator for meeting risk identification.
Given the original transcript and extracted risks, evaluate them based on these criteria:

{criteria}

Original Transcript:
{transcript}

Extracted Risks:
{risks}

For each criterion, provide:
1. A score from 0-10
2. A brief explanation of your score (1-2 sentences)

Return your evaluation as a JSON object with this structure:
{{
    "scores": {{
        "impact": <score>,
        "likelihood": <score>,
        "specificity": <score>
    }},
    "explanations": {{
        "impact": "<explanation>",
        "likelihood": "<explanation>",
        "specificity": "<explanation>"
    }},
    "overall_score": <weighted average>
}}
"""
        )
        
    def _format_criteria(self, component: str) -> str:
        """Format criteria descriptions for prompts."""
        criteria = self.schema['components'][component]['criteria']
        descriptions = self.schema['components'][component]['descriptions']
        
        formatted = []
        for criterion in criteria:
            formatted.append(f"- {criterion}: {descriptions[criterion]}")
        
        return "\n".join(formatted)
        
    def _calculate_weighted_score(self, scores: Dict[str, float], component: str) -> float:
        """Calculate weighted average score for a component."""
        weights = self.schema['components'][component]['weights']
        total_score = 0
        
        for criterion, score in scores.items():
            weight = weights.get(criterion, 0)
            total_score += score * weight
            
        return round(total_score, 2)
        
    async def evaluate_component(
        self,
        component: str,
        transcript: str,
        extracted_data: Any,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Evaluate a single component of the extraction."""
        try:
            # Format input data
            if isinstance(extracted_data, list):
                data_str = json.dumps(extracted_data, indent=2)
            else:
                data_str = str(extracted_data)
                
            # Get criteria
            criteria_str = self._format_criteria(component)
            
            # Create chain
            chain = LLMChain(
                llm=self.llm,
                prompt=self.prompts[component],
                verbose=False
            )
            
            # Run evaluation
            callbacks = [tracer] if langsmith_client else []
            result = await chain.arun(
                transcript=transcript,
                **{component: data_str},
                criteria=criteria_str,
                callbacks=callbacks
            )
            
            # Parse JSON result with error handling
            try:
                # Clean the result - extract JSON if there's extra text
                result_clean = result.strip()
                if result_clean.startswith('```json'):
                    result_clean = result_clean.replace('```json', '').replace('```', '').strip()
                
                # Extract JSON from text that may have explanations
                import re
                json_match = re.search(r'\{[\s\S]*\}', result_clean)
                if json_match:
                    result_clean = json_match.group(0)
                
                evaluation = json.loads(result_clean)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM response: {result[:200]}...")
                # Return a fallback evaluation
                criteria = self.schema['components'][component]['criteria']
                evaluation = {
                    'scores': {criterion: 5.0 for criterion in criteria},
                    'explanations': {criterion: "Unable to parse LLM response" for criterion in criteria},
                    'overall_score': 5.0,
                    'parse_error': str(e)
                }
            
            # Add metadata
            evaluation['metadata'] = {
                'component': component,
                'judge_model': self.judge_model,
                'prompt_version': '1.0',
                'timestamp': datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating {component}: {e}")
            return {
                'error': str(e),
                'component': component,
                'scores': {criterion: 0 for criterion in self.schema['components'][component]['criteria']},
                'overall_score': 0
            }
            
    async def evaluate_all(
        self,
        transcript: str,
        extraction_results: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Evaluate all components of the extraction."""
        # Create parallel evaluation tasks
        evaluation_tasks = {}
        
        for component in ['summary', 'decisions', 'action_items', 'risks']:
            if component in extraction_results:
                evaluation_tasks[component] = self.evaluate_component(
                    component,
                    transcript,
                    extraction_results[component],
                    metadata
                )
                
        # Run evaluations in parallel
        evaluations = {}
        for component, task in evaluation_tasks.items():
            evaluations[component] = await task
            
        # Calculate aggregate scores
        total_score = 0
        component_count = 0
        
        for component, eval_result in evaluations.items():
            if 'overall_score' in eval_result:
                total_score += eval_result['overall_score']
                component_count += 1
                
        aggregate_score = round(total_score / component_count, 2) if component_count > 0 else 0
        
        # Determine quality level
        quality_level = self._get_quality_level(aggregate_score)
        
        return {
            'evaluations': evaluations,
            'aggregate_score': aggregate_score,
            'quality_level': quality_level,
            'metadata': {
                'evaluation_timestamp': datetime.utcnow().isoformat(),
                'judge_model': self.judge_model,
                'schema_version': self.schema['schema_version'],
                **(metadata or {})
            }
        }
        
    def _get_quality_level(self, score: float) -> str:
        """Get quality level based on score."""
        levels = self.schema['scoring']['scale']['levels']
        
        for range_str, level in levels.items():
            min_score, max_score = map(int, range_str.split('-'))
            if min_score <= score <= max_score:
                return level
                
        return "Unknown"
        
    def get_improvement_suggestions(self, evaluation_results: Dict[str, Any]) -> List[str]:
        """Generate improvement suggestions based on evaluation results."""
        suggestions = []
        thresholds = self.schema['scoring']['thresholds']
        
        for component, eval_data in evaluation_results['evaluations'].items():
            if 'scores' in eval_data:
                for criterion, score in eval_data['scores'].items():
                    if score < thresholds['pass']:
                        explanation = eval_data.get('explanations', {}).get(criterion, '')
                        suggestions.append(
                            f"{component.title()} - {criterion}: Score {score}/10. {explanation}"
                        )
                        
        return suggestions