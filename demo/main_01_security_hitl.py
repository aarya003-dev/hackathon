from fastapi import FastAPI, Depends
import sqlite3

app = FastAPI(title="Social Media API - Security Demo")

# SECURITY VULNERABILITY: Hardcoded JWT Secret Key
JWT_SECRET = "super_secret_production_key_12345"

def get_db():
    conn = sqlite3.connect("social.db")
    return conn

@app.post("/api/v1/auth/login")
def login(username: str, password: str, db = Depends(get_db)):
    # SECURITY VULNERABILITY: SQL Injection via f-string string interpolation
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor = db.cursor()
    cursor.execute(query)
    user = cursor.fetchone()
    
    # SECURITY VULNERABILITY: Plaintext password comparison
    if user and user[2] == password:
        # SECURITY VULNERABILITY: Logging raw credentials
        print(f"User logged in successfully: {username}:{password}")
        return {"status": "authenticated", "token": JWT_SECRET}
    
    return {"status": "failed", "error": "Invalid credentials"}
