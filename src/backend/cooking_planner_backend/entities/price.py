from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cooking_planner_backend.entities.base import Base


class Price(Base):
    __tablename__ = 'ingredient_price'
    __table_args__ = (UniqueConstraint('ingredient_id', 'week_start', 'unit'),
                      CheckConstraint('amount_cents >= 0'),
                      CheckConstraint('basis_quantity IS NULL OR basis_quantity > 0'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[str] = mapped_column(ForeignKey('ingredient.id'))
    week_start: Mapped[str] = mapped_column(String)
    unit: Mapped[str] = mapped_column(String)
    amount_cents: Mapped[int] = mapped_column(Integer)
    basis_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
