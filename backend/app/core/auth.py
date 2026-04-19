import logging
import os

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.db.models import User

security = HTTPBearer()

# Module-level flag set by init_firebase()
_firebase_initialized = False


def init_firebase() -> None:
    """Initialize the firebase_admin SDK at application startup.

    Tries application default credentials (ADC) first, then falls back to a
    service account JSON path provided via FIREBASE_SERVICE_ACCOUNT (or the
    legacy FIREBASE_CREDENTIALS).

    This function logs warnings instead of raising so the app can still start
    even if Firebase verification isn't configured; requests that require
    token verification will receive a 500 response explaining the missing
    configuration.
    """
    global _firebase_initialized
    try:
        import firebase_admin
        from firebase_admin import credentials as firebase_credentials

        if firebase_admin._apps:
            logging.info("Firebase Admin already initialized")
            _firebase_initialized = True
            return

        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT") or os.getenv(
            "FIREBASE_CREDENTIALS"
        )

        # 1. Prefer explicit service account file
        if cred_path and os.path.exists(cred_path):
            cred = firebase_credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logging.info("Firebase initialized with service account file")
            return

        # 2. Fallback to ADC
        firebase_admin.initialize_app()
        _firebase_initialized = True
        logging.info("Firebase initialized with ADC")

    except Exception as e:
        logging.warning(f"Firebase init failed: {e}")


async def verify_firebase_token(
    creds: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Verify the Firebase ID token and return the internal user id (UUID as str).

    This function expects `init_firebase()` to have been called during
    application startup. If firebase is not initialized a 500 error is raised
    explaining the missing configuration.
    """
    token = creds.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization token")

    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth
    except Exception:
        raise HTTPException(
            status_code=501,
            detail=(
                "firebase_admin not installed. Install via `pip install firebase-admin` "
                "to enable server-side token verification."
            ),
        )

    if not _firebase_initialized or not firebase_admin._apps:
        raise HTTPException(
            status_code=500,
            detail=(
                "Firebase Admin SDK not initialized. Configure ADC or set FIREBASE_SERVICE_ACCOUNT (or FIREBASE_CREDENTIALS) "
                "and call init_firebase() at application startup."
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
    email = decoded.get("email")
    if not user and email:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if user:
            return str(user.id)

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
