from fastapi import Header
from fastapi import HTTPException


def get_authenticated_user_data(
        user_id: str | None = Header(None, alias="Bh-User-Id")
) -> dict:
    """
    Get authenticated user data from the request headers.

    Returns:
        dict: Dictionary containing user data.
    """
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="Missing Bh-User-Id header")

        user_data = {
            "user_id": user_id
        }

        return user_data

    except HTTPException as e:
        raise

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))
