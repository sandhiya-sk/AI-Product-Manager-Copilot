"""
database/test_endpoints.py — Programmatic integration test for Modules 1–3 endpoints
"""

import os
import sys
import requests
import json

def run_tests():
    base_url = "http://127.0.0.1:5000/api"
    print("=== STARTING INTEGRATION TESTS FOR MODULES 1-3 ===")
    
    # 1. Login PM User
    print("\n1. Testing Auth Login...")
    login_payload = {
        "email": "pm@company.com",
        "password": "password123"
    }
    
    try:
        res = requests.post(f"{base_url}/auth/login", json=login_payload)
        print(f"Status: {res.status_code}")
        response_data = res.json()
        print(json.dumps(response_data, indent=2))
        
        if not response_data.get("success"):
            print("Login failed. Skipping other tests.")
            return False
            
        token = response_data["data"]["access_token"]
        project_id = response_data["data"]["project_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
    except Exception as e:
        print(f"Login request failed: {e}")
        return False
        
    # 2. Ingest Single Form Feedback
    print("\n2. Testing Single Feedback Ingestion...")
    feedback_payload = {
        "subject": "Form test submission",
        "description": "This is a detailed description of the form test submission. It has enough words.",
        "priority": "High",
        "category": "Bug",
        "tags": "test, form, submission",
        "product_name": "PMCopilot",
        "product_version": "1.0",
        "sentiment_self_reported": "Neutral"
    }
    
    try:
        res = requests.post(f"{base_url}/ingest/feedback", json=feedback_payload, headers=headers)
        print(f"Status: {res.status_code}")
        print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print(f"Single feedback ingestion failed: {e}")
        
    # 3. Ingest CSV File
    print("\n3. Testing CSV Feedback Ingestion...")
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_feedback.csv")
    if not os.path.exists(csv_path):
        print(f"CSV file not found at: {csv_path}")
    else:
        try:
            with open(csv_path, 'rb') as f:
                files = {'file': f}
                data = {'project_id': project_id}
                res = requests.post(f"{base_url}/ingest/csv", files=files, data=data, headers=headers)
                print(f"Status: {res.status_code}")
                print(json.dumps(res.json(), indent=2))
        except Exception as e:
            print(f"CSV feedback ingestion failed: {e}")
            
    # 4. Trigger NLP Preprocessing Pipeline
    print("\n4. Triggering NLP Pipeline...")
    try:
        res = requests.post(f"{base_url}/process/run", json={"project_id": project_id}, headers=headers)
        print(f"Status: {res.status_code}")
        run_data = res.json()
        print(json.dumps(run_data, indent=2))
        
        if run_data.get("success"):
            job_id = run_data["data"]["job_id"]
            
            # Wait for background job to finish
            print("\n5. Polling Job Status...")
            import time
            for _ in range(10):
                time.sleep(2)
                status_res = requests.get(f"{base_url}/process/status/{job_id}", headers=headers)
                status_data = status_res.json()
                print(f"Job Status: {status_data['data']['status']}")
                if status_data["data"]["status"] in ("completed", "failed"):
                    print(json.dumps(status_data, indent=2))
                    break
                    
            # 6. Get Processed Results
            print("\n6. Fetching Processed Results...")
            results_res = requests.get(f"{base_url}/process/results?project_id={project_id}", headers=headers)
            print(f"Status: {results_res.status_code}")
            results_data = results_res.json()
            print(f"Total processed feedbacks: {results_data['data']['total']}")
            print("First item detail:")
            if results_data['data']['results']:
                print(json.dumps(results_data['data']['results'][0], indent=2))
                
    except Exception as e:
        print(f"NLP processing trigger failed: {e}")
        
    return True

if __name__ == "__main__":
    run_tests()
