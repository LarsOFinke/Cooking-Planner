from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from cooking_planner_backend.entities.Base import Base


class Marker(Base):
    __tablename__ = 'migration_marker'
    name: Mapped[str] = mapped_column(String, primary_key=True)
