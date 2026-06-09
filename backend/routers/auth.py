import os
import time
import jwt
from fastapi import APIRouter, Request, Response, HTTPException, status
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

router = APIRouter()

class GoogleAuthRequest(BaseModel):
    id_token: str

@router.post("/api/auth/google")
async def authenticate_google(request: GoogleAuthRequest, response: Response):
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")

    try:
        # Verify the token
        id_info = id_token.verify_oauth2_token(
            request.id_token,
            google_requests.Request(),
            audience=client_id
        )
        email = id_info.get("email")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    # Check authorized emails
    authorized_emails = os.environ.get("AUTHORIZED_EMAILS", "")
    allowed_list = [e.strip() for e in authorized_emails.split(",") if e.strip()]
    if email not in allowed_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized email")

    # Generate internal JWT
    jwt_secret = os.environ.get("NEXUS_HMAC_SECRET", "default_secret")
    exp = int(time.time()) + (24 * 3600)
    payload = {
        "email": email,
        "exp": exp
    }
    encoded_jwt = jwt.encode(payload, jwt_secret, algorithm="HS256")

    # Set HttpOnly cookie
    response.set_cookie(
        key="nexus_session",
        value=encoded_jwt,
        httponly=True,
        secure=True,
        samesite='strict'
    )
    return {"status": "ok"}

@router.get("/api/auth/status")
async def auth_status(request: Request):
    token = request.cookies.get("nexus_session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session")

    jwt_secret = os.environ.get("NEXUS_HMAC_SECRET", "default_secret")
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        return {"status": "ok", "email": payload.get("email")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
