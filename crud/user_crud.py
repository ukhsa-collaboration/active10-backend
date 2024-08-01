from typing import Union

from sqlalchemy.orm import Session
from fastapi import Depends
from models.user import User
from db.session import get_db_session


class UserCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:
        self.db = db

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_sub(self, uuid: str) -> Union[User, None]:
        return self.db.query(User).filter(User.unique_id == uuid).first()

    def update_user(self, user: User) -> Union[User, None]:
        existing_user = self.db.query(User).filter(User.unique_id == user.unique_id).first()
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

    def upsert_user(self, user: User) -> User:
        existing_user = self.db.query(User).filter(User.unique_id == user.unique_id).first()
        if existing_user:
            existing_user.first_name = user.first_name
            existing_user.email = user.email
            existing_user.date_of_birth = user.date_of_birth
            existing_user.gender = user.gender
            existing_user.postcode = user.postcode
        else:
            self.db.add(user)
        self.db.commit()
        self.db.refresh(existing_user if existing_user else user)
        return existing_user if existing_user else user

    def delete_user(self, uuid: str) -> Union[User, None]:
        pass
