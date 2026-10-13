from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from cooking_planner_backend.entities.Base import Base


class Ingredient(Base):
    __tablename__ = 'ingredient'
    id: Mapped[str] = mapped_column(String, primary_key=True)
