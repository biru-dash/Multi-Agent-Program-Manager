"""File-based storage utilities for meeting results."""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from numbers import Number

import numpy as np


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
    
    def _sanitize_for_json(self, obj: Any) -> Any:
        """Recursively sanitize data structure for JSON serialization."""
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, (set, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, np.ndarray):
            return self._sanitize_for_json(obj.tolist())
        elif isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, Number):
            # Handles other numeric types like Decimal
            return float(obj)
        elif hasattr(obj, '__dict__'):
            # Convert objects to dict
            return self._sanitize_for_json(obj.__dict__)
        else:
            # Convert to string as fallback
            return str(obj)
    
    def save_results(self, job_id: str, results: Dict[str, Any]) -> Path:
        """Save processing results to job directory."""
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize results for JSON serialization
        sanitized_results = self._sanitize_for_json(results)
        
        # Save full report as JSON
        report_path = job_dir / "full_report.json"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(sanitized_results, f, indent=2, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            # If serialization fails, try to save a minimal version
            print(f"Warning: Failed to serialize full results: {e}")
            minimal_results = {
                "summary": sanitized_results.get("summary", ""),
                "decisions": sanitized_results.get("decisions", []),
                "action_items": sanitized_results.get("action_items", []),
                "risks": sanitized_results.get("risks", []),
                "metadata": sanitized_results.get("metadata", {}),
                "error": f"Partial save due to serialization error: {str(e)}"
            }
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(minimal_results, f, indent=2, ensure_ascii=False)
        
        # Save markdown report
        md_path = job_dir / "report.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown_report(results))
        
        # Save individual components
        if "summary" in sanitized_results:
            summary_path = job_dir / "summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump({"summary": sanitized_results["summary"]}, f, indent=2)
        
        extracted_path = job_dir / "extracted_items.json"
        with open(extracted_path, 'w', encoding='utf-8') as f:
            json.dump({
                "decisions": sanitized_results.get("decisions", []),
                "action_items": sanitized_results.get("action_items", []),
                "risks": sanitized_results.get("risks", [])
            }, f, indent=2)
        
        return job_dir
    
    def get_results(self, job_id: str) -> Dict[str, Any]:
        """Load results from job directory."""
        job_dir = self.output_dir / job_id
        report_path = job_dir / "full_report.json"
        
        if not report_path.exists():
            raise FileNotFoundError(f"Results for job {job_id} not found")
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Try to read the file content to see what's wrong
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"JSON decode error at line {e.lineno}, column {e.colno}")
                print(f"Error context: {content[max(0, e.pos-100):e.pos+100]}")
            
            # Try to load from extracted_items.json as fallback
            extracted_path = job_dir / "extracted_items.json"
            if extracted_path.exists():
                try:
                    with open(extracted_path, 'r', encoding='utf-8') as f:
                        extracted = json.load(f)
                    summary_path = job_dir / "summary.json"
                    summary = ""
                    if summary_path.exists():
                        try:
                            with open(summary_path, 'r', encoding='utf-8') as f:
                                summary_data = json.load(f)
                                summary = summary_data.get("summary", "")
                        except:
                            pass
                    
                    return {
                        "summary": summary,
                        "decisions": extracted.get("decisions", []),
                        "action_items": extracted.get("action_items", []),
                        "risks": extracted.get("risks", [])
                    }
                except:
                    pass
            
            raise ValueError(f"Invalid JSON in results file: {str(e)}")
    
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
                decision_text = decision.get("text", decision.get("decision", ""))
                title = decision.get("title")
                rationale = decision.get("rationale")
                participants = decision.get("participants", [])
                
                # Format decision with title if available
                if title:
                    md.append(f"{i}. **{title}**: {decision_text}")
                else:
                    md.append(f"{i}. {decision_text}")
                
                if participants and participants != ["Unclear"]:
                    md.append(f"   - Participants: {', '.join(participants)}")
                elif speaker and speaker != "Unknown":
                    md.append(f"   - Speaker: {speaker}")
                
                if rationale:
                    md.append(f"   - Rationale: {rationale}")
                
                md.append(f"   {confidence_badge}\n")
            md.append("\n")
        
        # Action Items - Group by owner
        actions = results.get("action_items", [])
        if actions:
            md.append("## Action Items\n")
            
            # Group actions by owner
            actions_by_owner = {}
            unassigned = []
            
            for action in actions:
                owner = action.get("owner", "Unclear")
                if owner and owner != "Unclear" and owner != "Unassigned":
                    if owner not in actions_by_owner:
                        actions_by_owner[owner] = []
                    actions_by_owner[owner].append(action)
                else:
                    unassigned.append(action)
            
            # Sort owners alphabetically
            sorted_owners = sorted(actions_by_owner.keys())
            
            # Add actions grouped by owner
            for owner in sorted_owners:
                md.append(f"### {owner}\n")
                for i, action in enumerate(actions_by_owner[owner], 1):
                    confidence_badge = self._get_confidence_badge(action.get("confidence", 0.5))
                    due_date = action.get("due_date")
                    priority = action.get("priority", "medium").upper()
                    
                    md.append(f"{i}. **{action['action']}**")
                    if due_date:
                        md.append(f"   - Due: {due_date}")
                    if priority and priority != "MEDIUM":
                        md.append(f"   - Priority: {priority}")
                    md.append(f"   {confidence_badge}\n")
                md.append("\n")
            
            # Add unassigned actions
            if unassigned:
                md.append("### Unassigned\n")
                for i, action in enumerate(unassigned, 1):
                    confidence_badge = self._get_confidence_badge(action.get("confidence", 0.5))
                    due_date = action.get("due_date")
                    priority = action.get("priority", "medium").upper()
                    
                    md.append(f"{i}. **{action['action']}**")
                    if due_date:
                        md.append(f"   - Due: {due_date}")
                    if priority and priority != "MEDIUM":
                        md.append(f"   - Priority: {priority}")
                    md.append(f"   {confidence_badge}\n")
                md.append("\n")
            
            md.append("\n")
        
        # Risks - format with titles and structured info
        risks = results.get("risks", [])
        if risks:
            md.append("## Risks\n")
            
            # Sort risks by priority (HIGH first)
            priority_order = {"HIGH": 0, "MEDIUM-HIGH": 1, "MEDIUM": 2, "LOW": 3}
            sorted_risks = sorted(risks, key=lambda r: priority_order.get(r.get("priority", "MEDIUM"), 2))
            
            for i, risk in enumerate(sorted_risks, 1):
                confidence_badge = self._get_confidence_badge(risk.get("confidence", 0.5))
                mentioned_by = risk.get("mentioned_by", "Unknown")
                priority = risk.get("priority", "MEDIUM")
                category = risk.get("category", "Other")
                impact = risk.get("impact")
                mitigation = risk.get("mitigation")
                owners = risk.get("owners") or ([risk.get("owner")] if risk.get("owner") else [])
                risk_title = risk.get("title")
                risk_description = risk.get("risk", "")
                
                # Format risk with title if available
                if risk_title:
                    md.append(f"{i}. **{risk_title}** ({priority} PRIORITY)")
                else:
                    md.append(f"{i}. {risk_description} ({priority} PRIORITY)")
                
                if risk_description and risk_title:
                    md.append(f"   - **Risk**: {risk_description}")
                
                if impact:
                    md.append(f"   - **Impact**: {impact}")
                
                if mitigation:
                    if isinstance(mitigation, list):
                        md.append(f"   - **Mitigation**:")
                        for mit in mitigation:
                            md.append(f"     - {mit}")
                    else:
                        md.append(f"   - **Mitigation**: {mitigation}")
                
                if owners:
                    owners_str = ', '.join([o for o in owners if o])
                    if owners_str:
                        md.append(f"   - **Owner**: {owners_str}")
                
                if mentioned_by and mentioned_by != "Unknown":
                    md.append(f"   - Mentioned by: {mentioned_by}")
                
                md.append(f"   {confidence_badge}\n")
            md.append("\n")
        
        return "\n".join(md)
    
    def save_job_status(self, job_id: str, status: Dict[str, Any]) -> None:
        """Save job status to disk for persistence across server reloads."""
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        status_path = job_dir / "status.json"
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Load job status from disk."""
        job_dir = self.output_dir / job_id
        status_path = job_dir / "status.json"
        
        if not status_path.exists():
            return None
        
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _get_confidence_badge(self, confidence: float) -> str:
        """Get markdown badge for confidence score."""
        if confidence >= 0.8:
            return "🟢 High Confidence"
        elif confidence >= 0.6:
            return "🟡 Medium Confidence"
        else:
            return "🔴 Low Confidence"
