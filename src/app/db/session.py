from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# CRITICAL: settings.DATABASE_URL must be 'mysql+aiomysql://user:pass@host/db'
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

async def get_db():
    """
    Standard FastAPI Dependency.
    The async with context manager ensures the session is closed automatically.
    """
    async with AsyncSessionLocal() as session:
        yield session