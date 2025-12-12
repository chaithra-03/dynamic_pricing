import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Collects in-process metrics:
      - total requests
      - total response time 
      - cache hits/misses 
    """

    def __init__(self, app, dispatch: Callable = None):
        super().__init__(app, dispatch=dispatch)

    async def dispatch(self, request: Request, call_next):
        try:
            metrics = request.app.state.metrics
        except Exception:
            request.app.state.metrics = {
                "requests": 0,
                "total_response_ms": 0.0,
                "cache_hits": 0,
                "cache_misses": 0,
            }
            metrics = request.app.state.metrics

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        try:
            metrics["requests"] = metrics.get("requests", 0) + 1
            metrics["total_response_ms"] = metrics.get("total_response_ms", 0.0) + elapsed_ms
        except Exception:
            pass

        return response
