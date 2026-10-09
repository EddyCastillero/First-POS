from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings

# 1. Validación de Variables de Entorno
class Settings(BaseSettings):
    DATABASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()

# 2. Formateo de la URL para SQLAlchemy (usando explícitamente el driver psycopg2)
url = settings.DATABASE_URL.replace("postgres://", "postgresql+psycopg2://")
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
SQLALCHEMY_DATABASE_URL = url

# 3. Creación del Engine (El puente físico hacia Postgres)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Fábrica de Sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. La Clase Base (La plantilla maestra para tus modelos)
Base = declarative_base()

# 6. Dependencia para inyectar la BD en FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()