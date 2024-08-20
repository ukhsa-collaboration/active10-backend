from typing import Union, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db_session
from models.user import User


class UserCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:
        self.db = db

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_id(self, uuid: str) -> Union[User, None]:
        return self.db.query(User).filter(User.id == uuid).first()

    def get_user_by_sub(self, uuid: str) -> Union[User, None]:
        return self.db.query(User).filter(User.unique_id == uuid).first()

    def update_user(self, user: User) -> Union[User, None]:
        existing_user = self.db.query(User).filter(User.id == user.id).first()
        if existing_user:
            existing_user.first_name = user.first_name
            existing_user.email = user.email
            existing_user.date_of_birth = user.date_of_birth
            existing_user.gender = user.gender
            existing_user.postcode = user.postcode
            self.db.commit()
            self.db.refresh(existing_user)
            return existing_user
        else:
            return None

    def delete_user(self, uuid: str) -> Optional[User]:
        user_to_delete = self.db.query(User).filter(User.id == uuid).first()
        if user_to_delete:
            self.db.delete(user_to_delete)
            self.db.commit()
            return user_to_delete
        else:
            return None

    def update_current_token(self, uuid: str, token: str) -> None:
        user_to_update = self.db.query(User).filter(User.id == uuid).first()

        if user_to_update:
            user_to_update.current_token = token
            self.db.commit()

        return None