import urllib.request
import json
import uuid
import sys

BASE_URL = "http://127.0.0.1:5000/api"

def make_request(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req_data = None
    if data:
        req_data = json.dumps(data).encode('utf-8')
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            return json.loads(res.read().decode('utf-8')), res.status
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode('utf-8'))
            return err_body, e.code
        except Exception:
            return {"error": e.reason}, e.code
    except Exception as e:
        return {"error": str(e)}, 500

def test_flow():
    print("=== Testing End-to-End full-stack flow ===")
    
    # 1. Register a new user
    email = f"pm_test_{uuid.uuid4().hex[:6]}@test.com"
    password = "password123"
    print(f"\n1. Registering user: {email}...")
    res, code = make_request("/auth/register", "POST", {
        "email": email,
        "password": password,
        "role": "product_manager",
        "full_name": "Verify PM"
    })
    print(f"Response (Code {code}):", json.dumps(res, indent=2))
    if code != 201:
        print("Registration failed.")
        sys.exit(1)
        
    # 2. Login
    print(f"\n2. Logging in as {email}...")
    res, code = make_request("/auth/login", "POST", {
        "email": email,
        "password": password
    })
    print(f"Response (Code {code}):", json.dumps(res, indent=2))
    if code != 200:
        print("Login failed.")
        sys.exit(1)
        
    token = res["data"]["access_token"]
    project_id = res["data"]["project_id"]
    print(f"JWT Token retrieved. Associated project ID: {project_id}")
    
    # 3. Trigger Ingest of some mock processed feedback (if needed) or run prioritization
    print("\n3. Running AI Prioritization (Module 6)...")
    res, code = make_request("/prioritize/run", "POST", {
        "project_id": project_id,
        "force": True
    }, token)
    print(f"Response (Code {code}):", json.dumps(res, indent=2))
    
    # 4. Fetch Prioritization results
    print("\n4. Fetching Prioritization Results (Module 6)...")
    res, code = make_request(f"/prioritize/results?project_id={project_id}", "GET", token=token)
    print(f"Response (Code {code}):", json.dumps(res, indent=2))
    
    # 5. Generate PRD (Module 8)
    print("\n5. Generating PRD (Module 8)...")
    res, code = make_request("/prd/generate-prd", "POST", {
        "project_id": project_id,
        "feature_name": "Multi-factor Authentication",
        "description": "Add secure MFA via authenticator app."
    }, token)
    print(f"Response (Code {code}):")
    if code == 200:
        print("PRD Text Sample:")
        print(res.get("prd")[:400] + "\n...")
    else:
        print(json.dumps(res, indent=2))
        
    print("\n=== End-to-End flow verification complete! ===")

if __name__ == "__main__":
    test_flow()
