# uvicorn main:app --reload --port 8000
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from db import engine, init_db
from helpers.config import Config
from models.schemas import HealthResponse
from routes import auth, gameify_routes, guardians_routes, progress_routes, session_routes, user_routes
from services.errors import ServiceError
from services.gameify_service import sync_starter_rewards

logging.basicConfig(level=Config.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ytg")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with Session(engine) as session:
        sync_starter_rewards(session)
    if Config.jwt_secret_is_ephemeral:
        log.warning("JWT_SECRET is not set: using a random secret, so everyone is signed out on restart.")
    elif len(Config.jwt_secret.encode()) < 32:
        log.warning("JWT_SECRET is shorter than 32 bytes; use a long random value.")
    log.info("YTG API ready (AI backend: %s)", session_routes.classifier.backend)
    yield


app = FastAPI(title="YTG API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(ServiceError)
async def service_error(_: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    # Log the details, but never send stack traces or internals to the client
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500, content={"detail": "Something went wrong on our side. Please try again."}
    )


app.include_router(auth.router)
app.include_router(user_routes.router)
app.include_router(guardians_routes.router)
app.include_router(gameify_routes.router)
app.include_router(session_routes.router)
app.include_router(progress_routes.router)
app.include_router(session_routes.dev_router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health():
    return HealthResponse(status="ok", ai_backend=session_routes.classifier.backend)
