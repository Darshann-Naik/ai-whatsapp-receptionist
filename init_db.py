import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from src.app.models.domain import Base  # Ensure this points to your Base model

# Import ALL your models here so SQLAlchemy knows they exist
# Example: from app.models.tenant import Tenant

async def init_models():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    print("🚀 Connecting to database to create tables...")
    async with engine.begin() as conn:
        # This command builds every table defined in your 'Base'
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Tables created successfully!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_models())