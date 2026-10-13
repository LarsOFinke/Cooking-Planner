from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cooking_planner_backend.entities.Base import Base


class Translation(Base):
    __tablename__ = 'ingredient_translation'
    __table_args__ = (UniqueConstraint('ingredient_id', 'locale'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[str] = mapped_column(ForeignKey('ingredient.id'))
    locale: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
