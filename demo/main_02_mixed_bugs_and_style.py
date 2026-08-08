from fastapi import FastAPI
import sys

app=FastAPI(title="Social Media - Style & Bugs")

# GLOBAL STATE BUG: Unbounded global list memory leak
ALL_POSTS = []

# BUG: Mutable default argument tags=[]
def add_post(title: str, content: str, tags=[]):
    tags.append("social")
    post = {"id": len(ALL_POSTS) + 1, "title": title, "content": content, "tags": tags}
    ALL_POSTS.append(post)
    return post

@app.post("/create-post")
def create_post_endpoint(title: str, content: str):
    # STYLE / BUG: Unhandled exception and silent failure
    try:
        res = add_post(title, content)
        return res
    except:
        # SILENT EXCEPTION SWALLOWING
        pass

@app.get("/posts/{post_id}")
def get_post(post_id: int):
    # BUG: Off-by-one / IndexError without HTTP 404 response
    return ALL_POSTS[post_id]
