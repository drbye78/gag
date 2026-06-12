"""User store with SQLAlchemy for PostgreSQL."""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)
Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(255), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(511), nullable=False)
    role = Column(String(50), default="user")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class UserStore:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_user(self, email: str) -> Optional[UserModel]:
        with self.Session() as session:
            return session.query(UserModel).filter(UserModel.email == email).first()

    def create_user(
        self,
        email: str,
        username: str,
        password_hash: str,
        role: str = "user",
    ) -> UserModel:
        with self.Session() as session:
            user = UserModel(
                id=f"user_{email}",
                email=email,
                username=username,
                password_hash=password_hash,
                role=role,
            )
            session.add(user)
            session.commit()
            return user

    def update_last_login(self, email: str):
        with self.Session() as session:
            user = session.query(UserModel).filter(UserModel.email == email).first()
            if user:
                user.last_login = datetime.utcnow()
                session.commit()

    def list_users(self, limit: int = 100, offset: int = 0) -> List[UserModel]:
        with self.Session() as session:
            return session.query(UserModel).limit(limit).offset(offset).all()

    def delete_user(self, email: str) -> bool:
        with self.Session() as session:
            user = session.query(UserModel).filter(UserModel.email == email).first()
            if user:
                session.delete(user)
                session.commit()
                return True
            return False


_user_store: Optional[UserStore] = None


def get_user_store(database_url: str = "postgresql://eis:eis@localhost:5432/eis") -> UserStore:
    global _user_store
    if _user_store is None:
        _user_store = UserStore(database_url)
    return _user_store
