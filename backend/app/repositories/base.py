from sqlalchemy.orm import Session


class BaseRepository:
    """Holds the DB session. All SQL / ORM access goes through repositories."""

    def __init__(self, db: Session):
        self.db = db

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
