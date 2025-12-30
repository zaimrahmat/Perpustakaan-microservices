import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

bearer = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_SUPER_SECRET")
JWT_ALG = os.getenv("JWT_ALG", "HS256")

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer)
):
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        # payload minimal: {"sub": "...", "r": "a/u", "exp": ...}
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau kadaluarsa."
        )

def require_admin(user=Depends(get_current_user)):
    # token ringkas: admin="a"
    if user.get("r") != "a":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: hanya admin."
        )
    return user
