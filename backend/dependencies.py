from fastapi import Request, HTTPException
import jwt
import os

NEXUS_HMAC_SECRET = os.environ.get("NEXUS_HMAC_SECRET", "default-secret-for-dev")

async def get_current_user(request: Request):
    """
    Validates JWT session cookies and extracts the authenticated user email.

    Layer Interactions:
    - Layer 1 (Foundation): Manages security and API access at the middleware level.

    State Interactions:
    - None

    Args/Returns:
    - Args: `request: Request` (FastAPI request object)
    - Returns: `str` (the authenticated user's email)
    """
    token = request.cookies.get("nexus_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, NEXUS_HMAC_SECRET, algorithms=["HS256"])
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
