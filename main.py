"""FastAPI server — exposes the /solve endpoint for the NM i AI Tripletex challenge."""

import asyncio
import base64
import logging
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent import run_agent
from tripletex_client import TripletexClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Tripletex Accounting Agent")

# In-process session memory keyed by Tripletex base_url (sandbox-scoped)
SESSION_MEMORY: dict[str, list[str]] = {}


@app.post("/")
@app.post("/solve")
async def solve(request: Request):
    body = await request.json()

    prompt: str = body["prompt"]
    raw_files: list[dict] = body.get("files", [])
    creds: dict = body["tripletex_credentials"]

    base_url: str = creds["base_url"]
    session_token: str = creds["session_token"]

    logger.info("Received task (len=%d chars)", len(prompt))
    logger.info("Prompt: %s", prompt[:300])

    # Decode attached files
    file_contents = []
    for f in raw_files:
        data_bytes = base64.b64decode(f["content_base64"])
        filename: str = f.get("filename", "attachment")
        # Guess media type from extension
        if filename.endswith(".pdf"):
            media_type = "application/pdf"
        elif filename.endswith(".png"):
            media_type = "image/png"
        elif filename.endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif filename.endswith(".webp"):
            media_type = "image/webp"
        elif filename.endswith(".gif"):
            media_type = "image/gif"
        else:
            media_type = "application/octet-stream"

        logger.info("Attached file: %s (%s, %d bytes)", filename, media_type, len(data_bytes))
        if media_type == "application/octet-stream":
            logger.warning("Unsupported file type for %s — will not be sent to model", filename)
            continue

        file_contents.append({
            "filename": filename,
            "media_type": media_type,
            "data": base64.b64encode(data_bytes).decode(),
        })

    client = TripletexClient(base_url=base_url, session_token=session_token)

    notes = SESSION_MEMORY.setdefault(base_url, [])

    try:
        await asyncio.to_thread(run_agent, prompt=prompt, tripletex_client=client, file_contents=file_contents, session_notes=notes)
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error during task: %s — %s", e.response.status_code, e.response.text)
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=200)
    except Exception as e:
        logger.exception("Unexpected error during task")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=200)

    return JSONResponse({"status": "completed"})


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        timeout_keep_alive=5,
        timeout_graceful_shutdown=30,
    )
