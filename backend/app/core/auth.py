from supabase import create_client, Client
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security = HTTPBearer()

supabase_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key,
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    Validate the Supabase JWT and return the user object.
    Used as a FastAPI dependency for protected routes.
    """
    try:
        token = credentials.credentials
        user_response = supabase_client.auth.get_user(token)
        if user_response and user_response.user:
            return {
                "id": str(user_response.user.id),
                "email": user_response.user.email,
            }
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
