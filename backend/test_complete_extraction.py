#!/usr/bin/env python3
"""Test complete extraction flow with Ollama"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.adapter import get_model_adapter
from app.extraction.specialized_extractors import ActionExtractor
from app.preprocessing.parser import TranscriptParser, TranscriptSegment

def test_complete_flow():
    print("🔍 Testing Complete Action Extraction Flow")
    print("=" * 60)
    
    # Load model adapter
    try:
        model_adapter = get_model_adapter("ollama")
        print("✅ Ollama adapter loaded")
    except Exception as e:
        print(f"❌ Failed to load Ollama adapter: {e}")
        return
    
    # Create test segments (similar to what would come from transcript)
    segments = [
        TranscriptSegment(
            speaker="David Chen",
            text="Sarah, can you take action on that? I'd like you to reach out to the Salesforce account manager by end of day tomorrow.",
            timestamp=None,
            start_time=0.0,
            end_time=5.0
        ),
        TranscriptSegment(
            speaker="Sarah Martinez", 
            text="Yes, I'll do that. I'll send an email to our account manager, Mike Hendricks, and CC the team.",
            timestamp=None,
            start_time=5.0,
            end_time=10.0
        ),
        TranscriptSegment(
            speaker="David Chen",
            text="Marcus, I want you to do two things: first, escalate to the internal security team lead, and second, get formal quotes from all three external auditors.",
            timestamp=None,
            start_time=10.0,
            end_time=18.0
        ),
        TranscriptSegment(
            speaker="Emily Wilson",
            text="I can schedule a three-way meeting with legal and our product team to resolve this.",
            timestamp=None,
            start_time=18.0,
            end_time=22.0
        )
    ]
    
    # Test ActionExtractor
    try:
        print("🤖 Testing ActionExtractor...")
        action_extractor = ActionExtractor(model_adapter, None)
        
        # Test extraction
        action_items = action_extractor.extract([], segments)
        
        print(f"✅ ActionExtractor returned {len(action_items)} action items:")
        for i, action in enumerate(action_items, 1):
            print(f"\n  {i}. Action: {action.get('action', 'N/A')}")
            print(f"     Owner: {action.get('owner', 'N/A')}")
            print(f"     Due: {action.get('due_date', 'N/A')}")
            print(f"     Priority: {action.get('priority', 'N/A')}")
            print(f"     Confidence: {action.get('confidence', 'N/A')}")
        
        # Test if empty
        if not action_items:
            print("❌ Action items list is empty!")
            print("   This indicates an issue in the extraction process")
        else:
            print(f"\n✅ Successfully extracted {len(action_items)} action items")
        
    except Exception as e:
        print(f"❌ ActionExtractor failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complete_flow()