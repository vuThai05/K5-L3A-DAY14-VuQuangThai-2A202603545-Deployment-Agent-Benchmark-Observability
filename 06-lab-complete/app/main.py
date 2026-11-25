"""Production-ready API with health, auth, rate and budget controls."""

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import (
    PRICE_INPUT_PER_1K,
    PRICE_OUTPUT_PER_1K,
    check_budget,
    record_cost,
    reset_current_api_key,
    set_current_api_key,
)
from app.rate_limiter import check_rate_limit
from app.redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask


class JsonFormatter(logging.Formatter):
    """Write each application log record as one valid JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "lvl": record.levelname,
                "event": record.getMessage(),
            },
            ensure_ascii=False,
        )


logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup")
    yield
    logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health():
    """Liveness check: the process is alive even when Redis is unavailable."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/ready")
def ready():
    """Readiness check: this instance can use its shared Redis state."""
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis is not ready")
    return {"ready": True}


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    """Authenticated request path; rate and cost state are shared through Redis."""
    token = set_current_api_key(api_key)
    started = time.perf_counter()
    try:
        check_rate_limit(api_key)
        input_tokens = max(1, len(body.question.split()) * 2)
        estimated_cost = (
            input_tokens / 1000 * PRICE_INPUT_PER_1K
            + 128 / 1000 * PRICE_OUTPUT_PER_1K
        )
        check_budget(estimated_cost)

        answer = llm_ask(body.question)
        output_tokens = max(1, len(answer.split()) * 2)
        total_cost = record_cost(input_tokens, output_tokens)
        logger.info(
            json.dumps(
                {
                    "event": "ask.complete",
                    "question_length": len(body.question),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "daily_cost_usd": total_cost,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
                ensure_ascii=False,
            )
        )
        return {"question": body.question, "answer": answer}
    finally:
        reset_current_api_key(token)
