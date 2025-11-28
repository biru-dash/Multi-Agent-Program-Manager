#!/usr/bin/env python3
"""Test the enhanced MIA directly without API"""

import json
from pathlib import Path
from app.preprocessing.parser import TranscriptParser
from app.preprocessing.cleaner import TranscriptCleaner
from app.models.adapter import get_model_adapter
from app.extraction.extractor import MeetingExtractor

# Read the Q4 Product Launch transcript
transcript_path = Path("../meeting_transcripts/Q4_Product_Launch_Planning_Meeting_20250315.txt")
with open(transcript_path, "r") as f:
    transcript_content = f.read()

print(f"Loaded transcript: {len(transcript_content)} characters")

# Initialize components
parser = TranscriptParser()
cleaner = TranscriptCleaner()
model_adapter = get_model_adapter("local")
extractor = MeetingExtractor(model_adapter, cleaner)

# Parse transcript
print("Parsing transcript...")
segments = parser.parse_text(transcript_content)
print(f"Parsed {len(segments)} segments")

# Process with advanced preprocessing
print("Processing with advanced preprocessing...")
processed_segments, metadata = cleaner.process(
    segments,
    remove_fillers=True,
    normalize_speakers=True,
    segment_topics=True,
    remove_small_talk=True,
    merge_short_turns=True
)
print(f"Processed to {len(processed_segments)} segments")

# Extract information
print("Extracting decisions, actions, and risks...")
results = extractor.process(processed_segments)

# Print results
print("\n=== EXTRACTION RESULTS ===")
print(f"\nDecisions extracted: {len(results.get('decisions', []))}")
for i, decision in enumerate(results.get('decisions', [])[:10], 1):
    print(f"  {i}. {decision.get('decision', 'N/A')}")
    if decision.get('rationale'):
        print(f"     Rationale: {decision.get('rationale')}")
    print(f"     Participants: {', '.join(decision.get('participants', []))}")
    print(f"     Confidence: {decision.get('confidence', 0)}")

print(f"\nAction Items extracted: {len(results.get('action_items', []))}")
for i, action in enumerate(results.get('action_items', [])[:15], 1):
    print(f"  {i}. Owner: {action.get('owner', 'N/A')} - {action.get('action', 'N/A')}")
    if action.get('due_date'):
        print(f"     Due: {action.get('due_date')}")
    print(f"     Priority: {action.get('priority', 'N/A')}")

print(f"\nRisks extracted: {len(results.get('risks', []))}")
for i, risk in enumerate(results.get('risks', [])[:15], 1):
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
print(f"Decisions count: {quality.get('decisions_count', 0)}")
print(f"Actions count: {quality.get('actions_count', 0)}")
print(f"Risks count: {quality.get('risks_count', 0)}")
print(f"Average confidence: {quality.get('avg_confidence', 0):.2f}")

# Compare to expected
print("\n=== COMPARISON TO EXPECTED ===")
print("Expected: 9 decisions, ~20 action items, ~18 risks")
print(f"Actual: {len(results.get('decisions', []))} decisions, {len(results.get('action_items', []))} action items, {len(results.get('risks', []))} risks")