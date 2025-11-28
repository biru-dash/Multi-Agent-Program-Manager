#!/usr/bin/env python3
"""Simple test script for MIA API endpoints."""
import requests
import time
import sys
from pathlib import Path

API_BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{API_BASE_URL}/health")
    assert response.status_code == 200
    print(f"✓ Health check passed: {response.json()}")


def test_upload_txt():
    """Test uploading a TXT transcript."""
    print("\nTesting TXT file upload...")
    test_file = Path(__file__).parent / "tests" / "sample_transcript.txt"
    
    if not test_file.exists():
        print(f"✗ Test file not found: {test_file}")
        return None
    
    with open(test_file, 'rb') as f:
        files = {'file': ('test.txt', f, 'text/plain')}
        response = requests.post(f"{API_BASE_URL}/api/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    print(f"✓ Upload successful: {data}")
    return data['upload_id']


def test_process(upload_id: str, model_strategy: str = "local", preprocessing: str = "basic"):
    """Test processing a transcript."""
    print(f"\nTesting processing (strategy={model_strategy}, preprocessing={preprocessing})...")
    
    response = requests.post(
        f"{API_BASE_URL}/api/process/{upload_id}",
        params={
            "model_strategy": model_strategy,
            "preprocessing": preprocessing
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    job_id = data['job_id']
    print(f"✓ Processing started: job_id={job_id}")
    return job_id


def test_status(job_id: str, timeout: int = 300):
    """Poll job status until completion."""
    print(f"\nPolling job status (timeout={timeout}s)...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{API_BASE_URL}/api/status/{job_id}")
        assert response.status_code == 200
        status = response.json()
        
        print(f"  Status: {status['status']} - {status['progress']}% - {status['message']}")
        
        if status['status'] == 'completed':
            print("✓ Processing completed!")
            return True
        elif status['status'] == 'failed':
            print(f"✗ Processing failed: {status.get('error', 'Unknown error')}")
            return False
        
        time.sleep(2)
    
    print(f"✗ Timeout after {timeout} seconds")
    return False


def test_results(job_id: str):
    """Test retrieving results."""
    print("\nTesting results retrieval...")
    response = requests.get(f"{API_BASE_URL}/api/results/{job_id}")
    
    assert response.status_code == 200
    results = response.json()
    print(f"✓ Results retrieved:")
    print(f"  Summary: {results.get('summary', 'N/A')[:100]}...")
    print(f"  Decisions: {len(results.get('decisions', []))}")
    print(f"  Action Items: {len(results.get('action_items', []))}")
    print(f"  Risks: {len(results.get('risks', []))}")
    return results


def test_export(job_id: str, format: str = "json"):
    """Test exporting results."""
    print(f"\nTesting export ({format})...")
    response = requests.get(
        f"{API_BASE_URL}/api/export/{job_id}",
        params={"format": format}
    )
    
    assert response.status_code == 200
    print(f"✓ Export successful: {len(response.content)} bytes")
    return response.content


def main():
    """Run all tests."""
    print("=" * 60)
    print("MIA API Test Suite")
    print("=" * 60)
    
    try:
        # Test health check
        test_health_check()
        
        # Test upload
        upload_id = test_upload_txt()
        if not upload_id:
            print("✗ Cannot proceed without upload_id")
            sys.exit(1)
        
        # Test processing with local strategy (faster)
        job_id = test_process(upload_id, model_strategy="local", preprocessing="basic")
        
        # Poll for completion
        if test_status(job_id, timeout=300):
            # Test results
            results = test_results(job_id)
            
            # Test export
            test_export(job_id, "json")
            test_export(job_id, "md")
            
            print("\n" + "=" * 60)
            print("✓ All tests passed!")
            print("=" * 60)
        else:
            print("\n✗ Tests failed - processing did not complete")
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to API. Make sure the server is running:")
        print("  cd backend && uvicorn app.main:app --reload")
        sys.exit(1)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
