#!/usr/bin/env python3
"""Test backend Ollama integration directly"""

import requests
import json
import time

def test_backend_ollama_integration():
    """Test the backend's Ollama integration through the API"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Backend Ollama Integration")
    print("=" * 50)
    
    # Step 1: Check if backend is running
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code != 200:
            print("❌ Backend not running")
            return
        print("✅ Backend is running")
    except:
        print("❌ Cannot connect to backend")
        return
    
    # Step 2: Select the Q4 transcript
    try:
        response = requests.post(
            f"{base_url}/api/transcripts/select?filename=Q4_Product_Launch_Planning_Meeting_20250315.txt"
        )
        if response.status_code != 200:
            print("❌ Failed to select transcript")
            return
        
        upload_data = response.json()
        upload_id = upload_data['upload_id']
        print(f"✅ Selected transcript, Upload ID: {upload_id}")
    except Exception as e:
        print(f"❌ Error selecting transcript: {e}")
        return
    
    # Step 3: Process with Ollama strategy
    try:
        print("🚀 Starting processing with Ollama strategy...")
        response = requests.post(
            f"{base_url}/api/process/{upload_id}?model_strategy=ollama&preprocessing=advanced"
        )
        
        if response.status_code != 200:
            print(f"❌ Processing failed: {response.status_code}")
            print(response.text)
            return
        
        process_data = response.json()
        job_id = process_data['job_id']
        print(f"✅ Processing started, Job ID: {job_id}")
    except Exception as e:
        print(f"❌ Error starting processing: {e}")
        return
    
    # Step 4: Poll for completion
    print("⏳ Waiting for processing to complete...")
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{base_url}/api/status/{job_id}")
            if response.status_code != 200:
                print("❌ Failed to get status")
                return
            
            status_data = response.json()
            status = status_data['status']
            progress = status_data.get('progress', 0)
            message = status_data.get('message', '')
            
            print(f"   Status: {status}, Progress: {progress}%, Message: {message}")
            
            if status == 'completed':
                print("✅ Processing completed!")
                break
            elif status == 'failed':
                print(f"❌ Processing failed: {status_data.get('error', 'Unknown error')}")
                return
            
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return
    else:
        print("❌ Processing timed out")
        return
    
    # Step 5: Get and analyze results
    try:
        response = requests.get(f"{base_url}/api/results/{job_id}")
        if response.status_code != 200:
            print("❌ Failed to get results")
            return
        
        results = response.json()
        
        print("\n📊 RESULTS ANALYSIS")
        print("=" * 30)
        
        decisions = results.get('decisions', [])
        actions = results.get('action_items', [])
        risks = results.get('risks', [])
        
        print(f"Decisions: {len(decisions)}")
        print(f"Actions: {len(actions)}")
        print(f"Risks: {len(risks)}")
        
        print(f"\n📋 SAMPLE DECISIONS:")
        for i, decision in enumerate(decisions[:3], 1):
            text = decision.get('text', decision.get('decision', 'N/A'))
            speaker = decision.get('speaker', decision.get('participants', 'N/A'))
            confidence = decision.get('confidence', 0)
            print(f"  {i}. {text[:100]}...")
            print(f"     Speaker: {speaker}, Confidence: {confidence:.2f}")
        
        print(f"\n✅ SAMPLE ACTIONS:")
        for i, action in enumerate(actions[:3], 1):
            action_text = action.get('action', 'N/A')
            owner = action.get('owner', 'N/A')
            confidence = action.get('confidence', 0)
            print(f"  {i}. {action_text[:80]}...")
            print(f"     Owner: {owner}, Confidence: {confidence:.2f}")
        
        print(f"\n⚠️ SAMPLE RISKS:")
        for i, risk in enumerate(risks[:3], 1):
            risk_text = risk.get('risk', 'N/A')
            mentioned_by = risk.get('mentioned_by', 'N/A')
            confidence = risk.get('confidence', 0)
            print(f"  {i}. {risk_text[:80]}...")
            print(f"     Mentioned by: {mentioned_by}, Confidence: {confidence:.2f}")
        
        # Quality Assessment
        print(f"\n🎯 QUALITY ASSESSMENT")
        print("=" * 25)
        
        # Check if results look like proper extraction vs fragments
        decision_quality = "GOOD" if len(decisions) < 15 and any(len(d.get('text', d.get('decision', ''))) > 30 for d in decisions[:3]) else "POOR"
        action_quality = "GOOD" if len(actions) < 30 and any(len(a.get('action', '')) > 20 for a in actions[:3]) else "POOR"
        risk_quality = "GOOD" if len(risks) < 25 and any(len(r.get('risk', '')) > 30 for r in risks[:3]) else "POOR"
        
        print(f"Decision Quality: {decision_quality}")
        print(f"Action Quality: {action_quality}")
        print(f"Risk Quality: {risk_quality}")
        
        overall = "SUCCESS" if decision_quality == "GOOD" and action_quality == "GOOD" and risk_quality == "GOOD" else "NEEDS WORK"
        print(f"Overall: {overall}")
        
        # Save results for inspection
        with open('backend_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Full results saved to backend_test_results.json")
        
    except Exception as e:
        print(f"❌ Error getting results: {e}")
        return

if __name__ == "__main__":
    test_backend_ollama_integration()