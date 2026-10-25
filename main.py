# uvicorn main:app --reload --port 8000
from sqlmodel import Session

from fastapi_config import app, create_db_and_tables, engine
from helpers.config import Config
from models.schemas import HealthResponse
from routes import auth, gameify_routes, guardians_routes, session_routes, user_routes
from services.gameify_service import _add_rewards

app.include_router(auth.router)
app.include_router(user_routes.router)
app.include_router(guardians_routes.router)
app.include_router(gameify_routes.router)
app.include_router(session_routes.router)
app.include_router(session_routes.dev_router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health():
    return HealthResponse(status="ok", ai_backend=session_routes.classifier.backend)


create_db_and_tables()
with Session(engine) as _session:
    _add_rewards(session=_session)  # seed the shop on first run

if Config.jwt_secret_is_ephemeral:
    print("⚠ JWT_SECRET is not set: using a random secret, so everyone is signed out on restart.")
print(f"✓ YTG API ready (AI backend: {session_routes.classifier.backend})")
