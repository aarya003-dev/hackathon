from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(
    title="Social Media API",
    description="Production-ready FastAPI Social Media service",
    version="1.0.0"
)

class PostCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, description="Post title")
    content: str = Field(..., min_length=1, max_length=5000, description="Post body")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional post tags")

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str]

# In-memory database
POSTS_STORE: List[PostResponse] = []

@app.post(
    "/api/v1/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post"
)
def create_post(payload: PostCreate):
    """Creates a new social media post with validated payload."""
    new_id = len(POSTS_STORE) + 1
    post = PostResponse(
        id=new_id,
        title=payload.title,
        content=payload.content,
        tags=payload.tags or []
    )
    POSTS_STORE.append(post)
    return post

@app.get(
    "/api/v1/posts/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_200_OK,
    summary="Get post by ID"
)
def get_post(post_id: int):
    """Retrieves a single post by its ID."""
    for post in POSTS_STORE:
        if post.id == post_id:
            return post
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Post with ID {post_id} not found"
    )
