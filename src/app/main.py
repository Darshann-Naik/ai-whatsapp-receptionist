import pathlib
import sys
from fastapi import FastAPI, Path
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
# Get the absolute path of the 'src' directory
# __file__ is L:\Ai_whastapp\src\app\main.py
# .parent is L:\Ai_whastapp\src\app
# .parent.parent is L:\Ai_whastapp\src
current_dir = pathlib.Path(__file__).resolve().parent
src_path = str(current_dir.parent)

if src_path not in sys.path:
    sys.path.append(src_path)
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.security import limiter

def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # 1. Register Rate Limiter
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # 2. Security: CORS Policy (Restrict this in Production)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Include Versioned API Router
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application

app = create_app()