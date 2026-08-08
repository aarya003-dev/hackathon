from fastapi import FastAPI
import time
import asyncio

app = FastAPI(title="Social Media - Performance Demo")

# Simulated database tables
USERS_DB = [{"id": i, "name": f"User_{i}"} for i in range(1, 50)]
POSTS_DB = [{"user_id": i % 10 + 1, "text": f"Post content {i}"} for i in range(100)]

@app.get("/api/v1/feed")
async def get_user_feed():
    # PERFORMANCE BUG: Blocking time.sleep inside async event loop blocks all concurrent requests
    time.sleep(3)
    
    feed = []
    # PERFORMANCE BUG: N+1 query pattern in loop
    for user in USERS_DB:
        user_posts = [p for p in POSTS_DB if p["user_id"] == user["id"]]
        feed.append({"user": user["name"], "posts": user_posts})
        
    return {"feed": feed}
