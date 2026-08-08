import logging
import time
import uuid

from fastapi import Request

logger = logging.getLogger("efi_ai.api")


async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info("request_id=%s method=%s path=%s status=%s elapsed_ms=%s", request_id, request.method, request.url.path, response.status_code, elapsed_ms)
    return response
