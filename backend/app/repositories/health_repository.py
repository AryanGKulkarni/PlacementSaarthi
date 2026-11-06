from sqlalchemy import text

from app.repositories.base import BaseRepository


class HealthRepository(BaseRepository):
    def ping(self) -> None:
        self.db.execute(text("SELECT 1"))
