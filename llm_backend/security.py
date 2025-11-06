import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# This tells FastAPI to look for a token in the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("firebase-service-key.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Warning: Could not initialize Firebase Admin SDK: {e}")
        pass

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Dependency to verify Firebase ID token.
    Returns the decoded token dictionary if valid.
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not validate credentials: {e}",
        )