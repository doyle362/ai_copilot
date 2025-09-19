import logging
from typing import Optional

from fastapi import FastAPI

from .config import settings

LOGGER = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ImportError:  # pragma: no cover - optional dependency
    trace = None
    TracerProvider = None
    FastAPIInstrumentor = None


def configure_tracing(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing if enabled."""
    if not settings.observability_tracing_enabled:
        LOGGER.info("Tracing disabled via configuration")
        return

    if trace is None or TracerProvider is None or FastAPIInstrumentor is None:
        LOGGER.warning("opentelemetry packages not installed; tracing disabled")
        return

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    exporter: Optional[object]
    if settings.otel_exporter_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_endpoint,
            insecure=settings.otel_exporter_insecure,
        )
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument_app(app)
    LOGGER.info("OpenTelemetry tracing enabled (exporter=%s)",
                settings.otel_exporter_endpoint or "console")


# Metrics support -------------------------------------------------------------
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse
import time

REGISTRY = CollectorRegistry()
REQUEST_COUNTER = Counter(
    "level_analyst_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY
)
REQUEST_LATENCY = Histogram(
    "level_analyst_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    registry=REGISTRY
)
REFRESH_COUNTER = Counter(
    "level_analyst_daily_refresh_total",
    "Daily refresh job executions",
    ["outcome"],
    registry=REGISTRY
)
REFRESH_LAST_RUN = Gauge(
    "level_analyst_daily_refresh_timestamp",
    "Unix timestamp of last daily refresh",
    registry=REGISTRY
)
REFRESH_LAST_DURATION = Gauge(
    "level_analyst_daily_refresh_duration_seconds",
    "Duration of last refresh run",
    registry=REGISTRY
)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # pragma: no cover - integration tested
        if not settings.observability_metrics_enabled:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        path = request.url.path
        REQUEST_COUNTER.labels(request.method, path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
        return response


def metrics_endpoint():
    async def _metrics(_: Request):
        if not settings.observability_metrics_enabled:
            return PlainTextResponse("metrics disabled", status_code=404)
        data = generate_latest(REGISTRY)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return _metrics


def record_refresh(outcome: str, duration_seconds: Optional[float] = None) -> None:
    if not settings.observability_metrics_enabled:
        return
    REFRESH_COUNTER.labels(outcome=outcome).inc()
    if duration_seconds is not None:
        REFRESH_LAST_DURATION.set(duration_seconds)
    REFRESH_LAST_RUN.set(time.time())


def configure_metrics(app: FastAPI) -> None:
    if not settings.observability_metrics_enabled:
        LOGGER.info("Prometheus metrics disabled via configuration")
        return

    app.add_middleware(RequestMetricsMiddleware)
    app.add_route("/metrics", metrics_endpoint())
    LOGGER.info("Prometheus metrics endpoint registered at /metrics")


def configure_observability(app: FastAPI) -> None:
    configure_tracing(app)
    configure_metrics(app)
