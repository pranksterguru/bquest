import argparse
import logging
import os
import uvicorn
import asyncio
from fastapi import FastAPI, APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from cache.core_cache import insert_core_cache
from configs.LoggerConfig import setup_logging
from services.startups import startups
from controllers.end_points import endpoints
from controllers.socket_handlers import ws_router, queue_consumer,start_multiple_consumers


insert_core_cache("environment", "dev")
insert_core_cache("uionly", "true")

setup_logging()
logger = logging.getLogger("my_logger")

app = FastAPI()

app.add_middleware( CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"],)

api_router = APIRouter()
api_router.include_router(endpoints, prefix="/api")
api_router.include_router(ws_router)
app.include_router(api_router)

app.mount("/static", StaticFiles(directory="/Users/guru/organized/EndureX/ui/static"), name="static")

INDEX_FILE = "/Users/guru/organized/EndureX/ui/index.html"

@app.get("/")
@app.get("/index.html")
async def serve_index():
    if os.path.exists(INDEX_FILE):
        return FileResponse(INDEX_FILE)
    return {"error": f"File not found at {INDEX_FILE}"}

# Catch-all to handle any other route (e.g., /chart) by serving the same index.html
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    if os.path.exists(INDEX_FILE):
        return FileResponse(INDEX_FILE)
    return {"error": f"File not found at {INDEX_FILE}"}

@app.on_event("startup")
async def start_consumer():
    startups()
    start_multiple_consumers()
    


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, workers=8)
