from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from tasks import scrape_sublinks_task
import redis
import json
from celery.result import GroupResult

app = FastAPI()

# Initialize Redis to store task status/results
r = redis.Redis(host='redis', port=6379, db=2)

# Input model accepts a list of URLs
class URLRequest(BaseModel):
    urls: List[str]


@app.post("/scrape/")
def scrape_urls(request: URLRequest):
    """Trigger scraping tasks for a list of URLs."""
    task_mapping = {}
    for url in request.urls:
        task = scrape_sublinks_task.delay(url)
        task_mapping[url] = task.id
    return {"tasks": task_mapping}



    
