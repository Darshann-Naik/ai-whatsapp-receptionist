from fastapi import Header, HTTPException, status
from app.core.config import settings

async def verify_admin_key(x_admin_token: str = Header(...)):
    """
    Simple header-based security for internal admin routes.
    Expects 'X-Admin-Token' in the request headers.
    """
    if x_admin_token != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Admin Token",
        )
    return x_admin_token