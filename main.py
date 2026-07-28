# # uvicorn main:app --reload
from routes import auth, user_routes, gameify_routes, guardians_routes, session_routes
from fastapi_config import app, create_db_and_tables, get_session
from services.gameify_service import _add_rewards
app.include_router(auth.router)
app.include_router(user_routes.router)
app.include_router(guardians_routes.router)
app.include_router(gameify_routes.router)
app.include_router(session_routes.router)

create_db_and_tables()
_add_rewards(session=next(get_session())) # set first rewards to shop