from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from .config import settings
from .db import db
from .scheduler import scheduler_manager
from .logging_utils import configure_logging
from .security import emit_security_warnings
from .observability import configure_observability
from .routes import health, metrics, insights, threads, memories, prompts, recommendations, changes, diag, analytics, auth
# from .routes import experiments  # Temporarily disabled due to FastAPI parameter error


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await db.initialize()
        logging.info("Level Analyst API started with database")
    except Exception as e:
        logging.warning(f"Database connection failed, running without DB: {e}")

    try:
        await scheduler_manager.start()
    except Exception as scheduler_error:
        logging.error("Failed to start scheduler: %s", scheduler_error, exc_info=True)

    yield

    # Shutdown
    try:
        await scheduler_manager.stop()
    except Exception as scheduler_error:
        logging.error("Failed to stop scheduler cleanly: %s", scheduler_error, exc_info=True)

    try:
        await db.close()
    except:
        pass
    logging.info("Level Analyst API stopped")


configure_logging()
emit_security_warnings()

app = FastAPI(
    title="Level Analyst API",
    description="AI Analyst module for Level Parking",
    version="0.1.0",
    lifespan=lifespan
)

configure_observability(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(diag.router)
app.include_router(metrics.router)
app.include_router(auth.router)
app.include_router(insights.router)
app.include_router(threads.router)
app.include_router(memories.router)
app.include_router(prompts.router)
app.include_router(recommendations.router)
app.include_router(changes.router)
app.include_router(analytics.router)
# app.include_router(experiments.router)  # Temporarily disabled

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the web component card
app.mount("/card", StaticFiles(directory="static/iframe", html=True), name="card")


@app.get("/")
async def root():
    return {
        "service": "Level Analyst API",
        "version": "0.1.0",
        "status": "running"
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "analyst.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True
    )
