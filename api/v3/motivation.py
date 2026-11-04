from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from auth.v3.dependencies import get_current_user
from crud.motivation_crud import UserMotivationCRUD
from models.motivation import UserMotivation
from models.user import User
from schemas.motivation import CreateUpdateUserMotivationRequest, UserMotivationResponse
from utils.custom_exceptions import CustomHTTPException, ErrorCode

router = APIRouter(prefix="/motivations", tags=["Motivations"])


def _get_own_motivation(
    crud: UserMotivationCRUD, motivation_id: UUID, user: User
) -> UserMotivation:
    motivation = crud.get_by_id(motivation_id)
    if not motivation or motivation.user_id != user.id:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            error_message="Motivation not found",
        )
    return motivation


@router.post("/", response_model=UserMotivationResponse, status_code=201)
def create_user_motivation(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: CreateUpdateUserMotivationRequest,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    return crud.create_motivation(current_user.id, payload)


@router.get("/", response_model=list[UserMotivationResponse])
def get_all_motivations(
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    return crud.get_all_by_user(current_user.id)


@router.get("/{motivation_id}", response_model=UserMotivationResponse)
def get_motivation_by_id(
    current_user: Annotated[User, Depends(get_current_user)],
    motivation_id: UUID,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    return _get_own_motivation(crud, motivation_id, current_user)


@router.put("/{motivation_id}", response_model=UserMotivationResponse)
def update_user_motivation(
    current_user: Annotated[User, Depends(get_current_user)],
    motivation_id: UUID,
    payload: CreateUpdateUserMotivationRequest,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    motivation = _get_own_motivation(crud, motivation_id, current_user)
    return crud.update_motivation(motivation, payload)


@router.delete("/{motivation_id}", status_code=204)
def delete_user_motivation(
    current_user: Annotated[User, Depends(get_current_user)],
    motivation_id: UUID,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    motivation = _get_own_motivation(crud, motivation_id, current_user)
    crud.delete_motivation(motivation)
