# uvicorn main:app --reload 8000
import fastapi
from sqlmodel import Session, create_engine, SQLModel
from fastapi.middleware.cors import CORSMiddleware

app = fastapi.FastAPI(title="YTG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your specific https://xxx.lovable.app domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, echo=True)


def get_session():
    with Session(engine) as session:
        yield session
        
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
