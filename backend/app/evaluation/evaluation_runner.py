"""Orchestration for running evaluations with LangSmith observability."""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

try:
    from langchain.callbacks.tracers import LangChainTracer
except ImportError:
    try:
        from langchain_community.callbacks.tracers import LangChainTracer
    except ImportError:
        LangChainTracer = None

from langsmith import Client

from app.config.settings import settings
from app.evaluation.evaluation_chain import EvaluationChain
from app.evaluation.metrics_evaluator import MetricsEvaluator
from app.evaluation.evaluation_aggregator import EvaluationAggregator
from app.utils.storage import StorageManager

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Orchestrates evaluation runs with LangSmith observability."""
    
    def __init__(self):
        """Initialize evaluation runner."""
        self.storage = StorageManager(
            output_dir=settings.output_dir,
            upload_dir=settings.upload_dir
        )
        
        # Initialize evaluators
        self.llm_evaluator = EvaluationChain()
        self.metrics_evaluator = MetricsEvaluator()
        self.aggregator = EvaluationAggregator()
        
        # LangSmith setup
        self.langsmith_client = None
        self.tracer = None
        if settings.langsmith_api_key and LangChainTracer:
            try:
                self.langsmith_client = Client(api_key=settings.langsmith_api_key)
                self.tracer = LangChainTracer(
                    project_name=settings.langsmith_project_name or "mia-evaluations",
                    client=self.langsmith_client
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith tracer: {e}")
                self.tracer = None
            
    async def run_evaluation(
        self,
        job_id: str,
        transcript: str,
        extraction_results: Dict[str, Any],
        reference_data: Optional[Dict[str, Any]] = None,
        human_eval: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run complete evaluation pipeline."""
        logger.info(f"Starting evaluation for job {job_id}")
        
        evaluation_results = {
            'job_id': job_id,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'running'
        }
        
        try:
            # Run LLM evaluation
            try:
                if self.llm_evaluator.model_adapter.is_available():
                    logger.info(f"Running LLM evaluation with {settings.evaluation_model_provider}")
                    llm_eval = await self.llm_evaluator.evaluate_all(
                        transcript,
                        extraction_results,
                        metadata={'job_id': job_id}
                    )
                    evaluation_results['llm_evaluation'] = llm_eval
                else:
                    logger.warning("LLM evaluation model not available")
                    llm_eval = None
            except Exception as e:
                logger.error(f"LLM evaluation failed: {e}")
                llm_eval = None
                
            # Run metrics evaluation
            logger.info("Running metrics evaluation...")
            metrics_eval = await self._run_metrics_evaluation(
                extraction_results,
                reference_data,
                transcript
            )
            evaluation_results['metrics_evaluation'] = metrics_eval
            
            # Aggregate evaluations
            logger.info("Aggregating evaluations...")
            aggregated = self.aggregator.aggregate_evaluations(
                llm_eval=llm_eval,
                human_eval=human_eval,
                metrics_eval=metrics_eval
            )
            evaluation_results['aggregated_evaluation'] = aggregated
            
            # Generate improvement report
            improvement_report = self.aggregator.generate_improvement_report(
                aggregated,
                extraction_results
            )
            evaluation_results['improvement_report'] = improvement_report
            
            # Log to LangSmith if available
            if self.langsmith_client:
                await self._log_to_langsmith(evaluation_results)
                
            # Save results
            self._save_evaluation_results(job_id, evaluation_results)
            
            evaluation_results['status'] = 'completed'
            logger.info(f"Evaluation completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error in evaluation: {e}")
            evaluation_results['status'] = 'failed'
            evaluation_results['error'] = str(e)
            
        return evaluation_results
        
    async def _run_metrics_evaluation(
        self,
        extraction_results: Dict[str, Any],
        reference_data: Optional[Dict[str, Any]],
        transcript: str
    ) -> Dict[str, Any]:
        """Run metrics-based evaluation."""
        metrics_results = {}
        
        # Evaluate summary
        if 'summary' in extraction_results:
            reference_summary = reference_data.get('summary') if reference_data else None
            metrics_results['summary'] = self.metrics_evaluator.evaluate_summary_metrics(
                extraction_results['summary'],
                reference_summary,
                transcript
            )
            
        # Evaluate decisions
        if 'decisions' in extraction_results:
            reference_decisions = reference_data.get('decisions') if reference_data else None
            metrics_results['decisions'] = self.metrics_evaluator.evaluate_extraction_metrics(
                extraction_results['decisions'],
                reference_decisions,
                'decisions'
            )
            
        # Evaluate action items
        if 'action_items' in extraction_results:
            reference_actions = reference_data.get('action_items') if reference_data else None
            metrics_results['action_items'] = self.metrics_evaluator.evaluate_extraction_metrics(
                extraction_results['action_items'],
                reference_actions,
                'action_items'
            )
            
        # Evaluate risks
        if 'risks' in extraction_results:
            reference_risks = reference_data.get('risks') if reference_data else None
            metrics_results['risks'] = self.metrics_evaluator.evaluate_extraction_metrics(
                extraction_results['risks'],
                reference_risks,
                'risks'
            )
            
        # Calculate aggregate metrics
        metrics_results['aggregate'] = self.metrics_evaluator.calculate_aggregate_metrics(
            metrics_results
        )
        
        return metrics_results
        
    async def _log_to_langsmith(self, evaluation_results: Dict[str, Any]):
        """Log evaluation results to LangSmith."""
        try:
            # Create a run for tracking
            run_name = f"mia_eval_{evaluation_results['job_id']}"
            
            # Log the evaluation as metadata (use "chain" as run_type)
            self.langsmith_client.create_run(
                name=run_name,
                run_type="chain",
                inputs={
                    "job_id": evaluation_results['job_id'],
                    "timestamp": evaluation_results['timestamp']
                },
                outputs=evaluation_results,
                tags=["mia", "evaluation", "automated"]
            )
            
            logger.info(f"Logged evaluation to LangSmith: {run_name}")
            
        except Exception as e:
            logger.error(f"Error logging to LangSmith: {e}")
            
    def _save_evaluation_results(self, job_id: str, results: Dict[str, Any]):
        """Save evaluation results to storage."""
        # Create evaluation directory
        eval_dir = Path(settings.output_dir) / job_id / "evaluation"
        eval_dir.mkdir(parents=True, exist_ok=True)
        
        # Save full results
        full_path = eval_dir / "evaluation_results.json"
        with open(full_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        # Save summary report
        if 'improvement_report' in results:
            report_path = eval_dir / "improvement_report.json"
            with open(report_path, 'w') as f:
                json.dump(results['improvement_report'], f, indent=2)
                
        # Save markdown report
        self._save_markdown_report(eval_dir, results)
        
    def _save_markdown_report(self, eval_dir: Path, results: Dict[str, Any]):
        """Save evaluation results as markdown report."""
        md_path = eval_dir / "evaluation_report.md"
        
        with open(md_path, 'w') as f:
            f.write("# Meeting Intelligence Evaluation Report\n\n")
            f.write(f"**Job ID**: {results['job_id']}\n")
            f.write(f"**Timestamp**: {results['timestamp']}\n")
            f.write(f"**Status**: {results['status']}\n\n")
            
            # Aggregate scores
            if 'aggregated_evaluation' in results:
                agg = results['aggregated_evaluation']
                f.write("## Overall Scores\n\n")
                f.write(f"**Aggregate Score**: {agg['aggregate_score']}/10\n")
                f.write(f"**Confidence**: {agg['confidence']}\n")
                f.write(f"**Sources**: {', '.join(agg['sources'])}\n\n")
                
                # Component scores
                f.write("### Component Scores\n\n")
                for component, data in agg['components'].items():
                    f.write(f"#### {component.title()}\n")
                    f.write(f"- Overall: {data['overall_score']}/10\n")
                    for criterion, score in data['scores'].items():
                        f.write(f"- {criterion}: {score}/10\n")
                    f.write("\n")
                    
            # Improvement recommendations
            if 'improvement_report' in results:
                report = results['improvement_report']
                f.write("## Improvement Recommendations\n\n")
                f.write(f"{report['summary']}\n\n")
                
                if report['strengths']:
                    f.write("### Strengths\n\n")
                    for strength in report['strengths']:
                        f.write(f"- {strength['description']} (Score: {strength['score']})\n")
                    f.write("\n")
                    
                if report['priority_improvements']:
                    f.write("### Priority Improvements\n\n")
                    for idx, improvement in enumerate(report['priority_improvements'], 1):
                        f.write(f"{idx}. **{improvement['component']} - {improvement['criterion']}**\n")
                        f.write(f"   - Current Score: {improvement['score']}/10\n")
                        f.write(f"   - Recommendation: {improvement['recommendation']}\n")
                        if improvement.get('details'):
                            f.write(f"   - Details: {improvement['details']}\n")
                        f.write("\n")
                        
    async def run_batch_evaluation(
        self,
        job_ids: List[str],
        parallel: bool = True
    ) -> Dict[str, Any]:
        """Run evaluations for multiple jobs."""
        results = {}
        
        if parallel:
            # Run evaluations in parallel
            tasks = []
            for job_id in job_ids:
                # Load extraction results
                try:
                    extraction_results = self.storage.get_results(job_id)
                    transcript = self._load_transcript(job_id)
                    
                    task = self.run_evaluation(
                        job_id,
                        transcript,
                        extraction_results
                    )
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"Error loading data for job {job_id}: {e}")
                    results[job_id] = {'status': 'failed', 'error': str(e)}
                    
            # Wait for all tasks
            if tasks:
                completed = await asyncio.gather(*tasks, return_exceptions=True)
                for job_id, result in zip(job_ids, completed):
                    if isinstance(result, Exception):
                        results[job_id] = {'status': 'failed', 'error': str(result)}
                    else:
                        results[job_id] = result
        else:
            # Run evaluations sequentially
            for job_id in job_ids:
                try:
                    extraction_results = self.storage.get_results(job_id)
                    transcript = self._load_transcript(job_id)
                    
                    results[job_id] = await self.run_evaluation(
                        job_id,
                        transcript,
                        extraction_results
                    )
                except Exception as e:
                    logger.error(f"Error evaluating job {job_id}: {e}")
                    results[job_id] = {'status': 'failed', 'error': str(e)}
                    
        return results
        
    def _load_transcript(self, job_id: str) -> str:
        """Load transcript text for a job."""
        # This is simplified - in production, track transcript with job
        # For now, return placeholder
        return "Transcript content would be loaded here"