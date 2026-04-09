import os

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.db.models import User

security = HTTPBearer()


async def verify_firebase_token(
    creds: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Verify the Firebase ID token and return the internal user id (UUID as str).

    Behavior:
    - Requires the `firebase_admin` package and properly configured credentials.
    - Verifies the ID token server-side and extracts `uid`, `email`, and `name` if present.
    - Looks up a `User` by `firebase_uid`; if missing, creates a new `User` row.
    - Returns `str(user.id)` which should be used as the canonical `user_id` for requests.

    Raises HTTPException with appropriate status codes when verification fails or the
    Firebase admin SDK is not configured.
    """
    token = creds.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization token")

    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth
        from firebase_admin import credentials as firebase_credentials
    except Exception:
        raise HTTPException(
            status_code=501,
            detail=(
                "firebase_admin not installed. Install via `pip install firebase-admin` "
                "and configure a service account (set FIREBASE_SERVICE_ACCOUNT env var)"
            ),
        )

    # Initialize firebase admin app if not already done. Prefer ADC but support
    # a service account JSON path via FIREBASE_SERVICE_ACCOUNT env var.
    if not firebase_admin._apps:
        try:
            # Try to initialize with default credentials (ADC) first
            firebase_admin.initialize_app()
        except Exception:
            cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")
            if cred_path and os.path.exists(cred_path):
                cred = firebase_credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Firebase Admin SDK not initialized. Set FIREBASE_SERVICE_ACCOUNT to a service account JSON "
                        "or configure application default credentials."
                    ),
                )

    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase ID token: {exc}")

    uid = decoded.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token: uid missing")

    # Map firebase uid to internal user, create if missing.
    stmt = select(User).where(User.firebase_uid == uid).limit(1)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        # Create a minimal user record using available token claims.
        email = decoded.get("email") or f"{uid}@unknown"
        name = decoded.get("name") or decoded.get("displayName") or "User"
        new_user = User(firebase_uid=uid, email=email, name=name)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user = new_user

    # Return internal user id as string (UUID).
    return str(user.id)
