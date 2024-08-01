from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException

from auth.auth_bearer import authenticated_user_id
from crud.user_crud import UserCRUD


def get_authenticated_user_data(
    user_id: Annotated[str, Depends(authenticated_user_id)],
    user_crud: Annotated[UserCRUD, Depends()]
):
    user_data = user_crud.get_user_by_sub(user_id)

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return user_data
