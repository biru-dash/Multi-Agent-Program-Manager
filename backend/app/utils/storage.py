"""File-based storage utilities for meeting results."""
import json
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uuid


class StorageManager:
    """Manages file-based storage for meeting processing results."""
    
    def __init__(self, output_dir: str = "./outputs", upload_dir: str = "./uploads"):
        """Initialize storage manager with directories."""
        self.output_dir = Path(output_dir)
        self.upload_dir = Path(upload_dir)
        
        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def save_upload(self, file_content: bytes, filename: str) -> str:
        """Save uploaded file and return upload_id."""
        upload_id = str(uuid.uuid4())
        upload_path = self.upload_dir / upload_id
        upload_path.mkdir(exist_ok=True)
        
        file_path = upload_path / filename
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return upload_id
    
    def get_upload_path(self, upload_id: str) -> Path:
        """Get path to uploaded file."""
        upload_path = self.upload_dir / upload_id
        if not upload_path.exists():
            raise FileNotFoundError(f"Upload {upload_id} not found")
        
        # Return first file found in upload directory
        files = list(upload_path.iterdir())
        if not files:
            raise FileNotFoundError(f"No files found for upload {upload_id}")
        
        return files[0]
    
    def save_results(self, job_id: str, results: Dict[str, Any]) -> Path:
        """Save processing results to job directory."""
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save full report as JSON
        report_path = job_dir / "full_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save markdown report
        md_path = job_dir / "report.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown_report(results))
        
        # Save individual components
        if "summary" in results:
            summary_path = job_dir / "summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump({"summary": results["summary"]}, f, indent=2)
        
        extracted_path = job_dir / "extracted_items.json"
        with open(extracted_path, 'w', encoding='utf-8') as f:
            json.dump({
                "decisions": results.get("decisions", []),
                "action_items": results.get("action_items", []),
                "risks": results.get("risks", [])
            }, f, indent=2)
        
        return job_dir
    
    def get_results(self, job_id: str) -> Dict[str, Any]:
        """Load results from job directory."""
        job_dir = self.output_dir / job_id
        report_path = job_dir / "full_report.json"
        
        if not report_path.exists():
            raise FileNotFoundError(f"Results for job {job_id} not found")
        
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable markdown report."""
        md = []
        md.append("# Meeting Intelligence Report\n")
        md.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        # Summary
        md.append("## Summary\n")
        md.append(results.get("summary", "No summary available."))
        md.append("\n")
        
        # Decisions
        decisions = results.get("decisions", [])
        if decisions:
            md.append("## Decisions\n")
            for i, decision in enumerate(decisions, 1):
                confidence_badge = self._get_confidence_badge(decision.get("confidence", 0.5))
                speaker = decision.get("speaker", "Unknown")
                md.append(f"{i}. {decision['text']} ({speaker}) {confidence_badge}\n")
            md.append("\n")
        
        # Action Items
        actions = results.get("action_items", [])
        if actions:
            md.append("## Action Items\n")
            for i, action in enumerate(actions, 1):
                confidence_badge = self._get_confidence_badge(action.get("confidence", 0.5))
                owner = action.get("owner", "Unassigned")
                due_date = action.get("due_date", "No due date")
                priority = action.get("priority", "medium").upper()
                md.append(
                    f"{i}. **{action['action']}**\n"
                    f"   - Owner: {owner}\n"
                    f"   - Due: {due_date}\n"
                    f"   - Priority: {priority} {confidence_badge}\n\n"
                )
            md.append("\n")
        
        # Risks
        risks = results.get("risks", [])
        if risks:
            md.append("## Risks\n")
            for i, risk in enumerate(risks, 1):
                confidence_badge = self._get_confidence_badge(risk.get("confidence", 0.5))
                mentioned_by = risk.get("mentioned_by", "Unknown")
                md.append(f"{i}. {risk['risk']} (mentioned by: {mentioned_by}) {confidence_badge}\n")
            md.append("\n")
        
        return "\n".join(md)
    
    def _get_confidence_badge(self, confidence: float) -> str:
        """Get markdown badge for confidence score."""
        if confidence >= 0.8:
            return "🟢 High Confidence"
        elif confidence >= 0.6:
            return "🟡 Medium Confidence"
        else:
            return "🔴 Low Confidence"
