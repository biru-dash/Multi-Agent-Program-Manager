#!/usr/bin/env python3
"""Test the enhanced MIA with Q4 Product Launch transcript"""

import requests
import json
import time
from pathlib import Path

# API endpoint
API_URL = "http://localhost:8000/api/process"

# Read the Q4 Product Launch transcript
transcript_path = Path("../meeting_transcripts/Q4_Product_Launch_Planning_Meeting_20250315.txt")
if not transcript_path.exists():
    print(f"Error: Transcript not found at {transcript_path}")
    exit(1)

with open(transcript_path, "r") as f:
    transcript_content = f.read()

# Prepare the request
files = {
    "file": ("Q4_Product_Launch_Planning_Meeting.txt", transcript_content, "text/plain")
}

data = {
    "preprocessing": "advanced",
    "model_strategy": "local"
}

print("Sending request to enhanced MIA...")
print(f"Transcript length: {len(transcript_content)} characters")

# Send request
try:
    response = requests.post(API_URL, files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        
        # Check job ID and poll for results
        job_id = result.get("job_id")
        if job_id:
            print(f"Job ID: {job_id}")
            print("Processing... (this may take a minute)")
            
            # Poll for results
            max_attempts = 60
            for attempt in range(max_attempts):
                time.sleep(2)
                status_response = requests.get(f"http://localhost:8000/api/jobs/{job_id}/status")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status")
                    
                    if status == "completed":
                        # Get full results
                        results_response = requests.get(f"http://localhost:8000/api/jobs/{job_id}/results")
                        if results_response.status_code == 200:
                            results = results_response.json()
                            
                            # Print summary of results
                            print("\n=== EXTRACTION RESULTS ===")
                            print(f"\nDecisions extracted: {len(results.get('decisions', []))}")
                            for i, decision in enumerate(results.get('decisions', [])[:5], 1):
                                print(f"  {i}. {decision.get('decision', 'N/A')}")
                                if decision.get('rationale'):
                                    print(f"     Rationale: {decision.get('rationale')}")
                            
                            print(f"\nAction Items extracted: {len(results.get('action_items', []))}")
                            for i, action in enumerate(results.get('action_items', [])[:10], 1):
                                print(f"  {i}. Owner: {action.get('owner', 'N/A')} - {action.get('action', 'N/A')}")
                                if action.get('due_date'):
                                    print(f"     Due: {action.get('due_date')}")
                            
                            print(f"\nRisks extracted: {len(results.get('risks', []))}")
                            for i, risk in enumerate(results.get('risks', [])[:10], 1):
                                print(f"  {i}. [{risk.get('category', 'N/A')}] {risk.get('risk', 'N/A')}")
                                print(f"     Mentioned by: {risk.get('mentioned_by', 'N/A')}")
                            
                            # Save full results
                            output_path = Path("enhanced_mia_test_results.json")
                            with open(output_path, "w") as f:
                                json.dump(results, f, indent=2)
                            print(f"\nFull results saved to: {output_path}")
                            
                            # Quality metrics
                            quality = results.get("quality_metrics", {})
                            print(f"\n=== QUALITY METRICS ===")
                            print(f"Summary length: {quality.get('summary_length', 0)}")
                            print(f"Average confidence: {quality.get('avg_confidence', 0):.2f}")
                            print(f"Quality warning: {results.get('quality_warning', False)}")
                            
                        break
                    elif status == "failed":
                        print(f"Processing failed: {status_data.get('error', 'Unknown error')}")
                        break
                    else:
                        print(f"Status: {status} (attempt {attempt + 1}/{max_attempts})")
        else:
            print("Error: No job ID returned")
            print(result)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Error: {str(e)}")