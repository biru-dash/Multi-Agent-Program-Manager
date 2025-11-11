#!/usr/bin/env python3
"""Test the enhanced MIA with Ollama/Llama 3 directly"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
from pathlib import Path
from app.preprocessing.parser import TranscriptParser
from app.preprocessing.cleaner import TranscriptCleaner
from app.models.adapter import get_model_adapter
from app.extraction.extractor import MeetingExtractor

def main():
    # Read the Q4 Product Launch transcript
    transcript_path = Path("../meeting_transcripts/Q4_Product_Launch_Planning_Meeting_20250315.txt")
    with open(transcript_path, "r") as f:
        transcript_content = f.read()

    print(f"🚀 Testing Enhanced MIA with Ollama/Llama 3")
    print(f"📄 Loaded transcript: {len(transcript_content)} characters")

    # Initialize components with Ollama
    print("🔧 Initializing components...")
    parser = TranscriptParser()
    cleaner = TranscriptCleaner()
    
    try:
        model_adapter = get_model_adapter("ollama")
        print("✅ Ollama adapter loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load Ollama adapter: {e}")
        return

    extractor = MeetingExtractor(model_adapter, cleaner)

    # Parse transcript
    print("📝 Parsing transcript...")
    segments = parser.parse_text(transcript_content)
    print(f"   Parsed {len(segments)} segments")

    # Process with advanced preprocessing
    print("⚙️ Processing with advanced preprocessing...")
    processed_segments, metadata = cleaner.process(
        segments,
        remove_fillers=True,
        normalize_speakers=True,
        segment_topics=True,
        remove_small_talk=True,
        merge_short_turns=True
    )
    print(f"   Processed to {len(processed_segments)} segments")

    # Extract information
    print("🤖 Extracting with Llama 3 via Ollama...")
    print("   This may take 1-2 minutes for the first run...")
    
    try:
        results = extractor.process(processed_segments)
        
        # Print results
        print("\n" + "="*60)
        print("🎯 EXTRACTION RESULTS")
        print("="*60)
        
        decisions = results.get('decisions', [])
        print(f"\n📋 DECISIONS EXTRACTED: {len(decisions)}")
        for i, decision in enumerate(decisions[:10], 1):
            print(f"  {i}. {decision.get('decision', 'N/A')}")
            if decision.get('rationale'):
                print(f"     💭 Rationale: {decision.get('rationale')}")
            print(f"     👥 Participants: {', '.join(decision.get('participants', []))}")
            print(f"     🎯 Confidence: {decision.get('confidence', 0):.2f}")
            print()

        action_items = results.get('action_items', [])
        print(f"\n✅ ACTION ITEMS EXTRACTED: {len(action_items)}")
        for i, action in enumerate(action_items[:15], 1):
            print(f"  {i}. 👤 {action.get('owner', 'N/A')} - {action.get('action', 'N/A')}")
            if action.get('due_date'):
                print(f"     ⏰ Due: {action.get('due_date')}")
            print(f"     🔥 Priority: {action.get('priority', 'N/A')} | Confidence: {action.get('confidence', 0):.2f}")
            print()

        risks = results.get('risks', [])
        print(f"\n⚠️ RISKS EXTRACTED: {len(risks)}")
        for i, risk in enumerate(risks[:15], 1):
            print(f"  {i}. [{risk.get('category', 'N/A')}] {risk.get('risk', 'N/A')}")
            print(f"     🗣️ Mentioned by: {risk.get('mentioned_by', 'N/A')} | Confidence: {risk.get('confidence', 0):.2f}")
            print()

        # Save full results
        output_path = Path("ollama_test_results.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"💾 Full results saved to: {output_path}")

        # Quality metrics
        quality = results.get("quality_metrics", {})
        print(f"\n📊 QUALITY METRICS")
        print("="*30)
        print(f"Summary length: {quality.get('summary_length', 0)}")
        print(f"Decisions count: {quality.get('decisions_count', 0)}")
        print(f"Actions count: {quality.get('actions_count', 0)}")
        print(f"Risks count: {quality.get('risks_count', 0)}")
        print(f"Average confidence: {quality.get('avg_confidence', 0):.2f}")

        # Compare to expected
        print(f"\n🎯 COMPARISON TO EXPECTED")
        print("="*35)
        print("Expected: 9 decisions, ~20 action items, ~18 risks")
        print(f"Actual:   {len(decisions)} decisions, {len(action_items)} action items, {len(risks)} risks")
        
        # Success metrics
        decision_success = len(decisions) >= 5  # At least half expected
        action_success = len(action_items) >= 10 and len(action_items) <= 30  # Reasonable range
        risk_success = len(risks) >= 8 and len(risks) <= 25  # Reasonable range
        
        print(f"\n🏆 SUCCESS METRICS")
        print("="*20)
        print(f"Decisions: {'✅ GOOD' if decision_success else '❌ POOR'}")
        print(f"Actions:   {'✅ GOOD' if action_success else '❌ POOR'}")
        print(f"Risks:     {'✅ GOOD' if risk_success else '❌ POOR'}")
        
        overall_success = decision_success and action_success and risk_success
        print(f"Overall:   {'🎉 SUCCESS!' if overall_success else '⚠️ NEEDS WORK'}")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()