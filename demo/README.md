# Social Media App - Demo main.py Sample Versions

This directory contains pre-configured `main.py` files designed to test and demonstrate different multi-agent code review outcomes in your React Dashboard (`http://localhost:5173`).

---

## ?? Sample Files Overview

| File | Purpose / Test Scenario | Expected Outcome |
| :--- | :--- | :--- |
| `main_01_security_hitl.py` | Critical Security Vulnerabilities (Plaintext Password Check, SQL Injection, Hardcoded JWT secret, Unmasked Credential Logging) | Triggers **Security Agent Critical finding** and pauses run at **`waiting_hitl`** (Human-In-The-Loop) |
| `main_02_mixed_bugs_and_style.py` | Style & Code Quality Issues (Mutable default args `tags=[]`, Unhandled exceptions, Silent `except: pass`, Missing 404 handler) | Triggers **Core Review Agent Warnings** & PEP8 suggestions |
| `main_03_performance_issue.py` | Performance & Concurrency Bottlenecks (Blocking `time.sleep` in async route, N+1 query loop, memory leaks) | Triggers **Core Review Performance Warnings** |
| `main_04_good_production.py` | Production-Grade Clean Code (Pydantic V2 schemas, proper HTTP error handling, OpenAPI docs) | Completes cleanly with **Status `succeeded`** & 0 critical errors |

---

## ?? How to Test Any Version

To test any version, simply copy it over to your watched repo's `app/main.py` and commit it in Git:

### Option 1: Test Security HITL Gate (`main_01_security_hitl.py`)
```powershell
Copy-Item -Force .\demo\main_01_security_hitl.py .\backend\data\repo\social-media-FastApi\app\main.py
git -C .\backend\data\repo\social-media-FastApi commit -am "test: add auth login endpoint with security vulnerabilities"
```

### Option 2: Test Style & Functional Bugs (`main_02_mixed_bugs_and_style.py`)
```powershell
Copy-Item -Force .\demo\main_02_mixed_bugs_and_style.py .\backend\data\repo\social-media-FastApi\app\main.py
git -C .\backend\data\repo\social-media-FastApi commit -am "test: add post endpoints with mutable defaults and swallow exceptions"
```

### Option 3: Test Performance & Concurrency (`main_03_performance_issue.py`)
```powershell
Copy-Item -Force .\demo\main_03_performance_issue.py .\backend\data\repo\social-media-FastApi\app\main.py
git -C .\backend\data\repo\social-media-FastApi commit -am "test: add feed endpoint with blocking sleep and N+1 queries"
```

### Option 4: Test Clean Production Code (`main_04_good_production.py`)
```powershell
Copy-Item -Force .\demo\main_04_good_production.py .\backend\data\repo\social-media-FastApi\app\main.py
git -C .\backend\data\repo\social-media-FastApi commit -am "test: refactor main app to production-grade pydantic schemas"
```

After running any of the above commands, open **`http://localhost:5173`** to watch the real-time agent graph and review output!
