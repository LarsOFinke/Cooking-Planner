"""SQLite engine, schema upgrade, and serialized SQLAlchemy sessions."""

from contextlib import contextmanager
from pathlib import Path
from threading import RLock

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from cooking_planner_backend.entities.Base import Base
from cooking_planner_backend.entities.Ingredient import Ingredient  # noqa: F401
from cooking_planner_backend.entities.Marker import Marker
from cooking_planner_backend.entities.Price import Price  # noqa: F401
from cooking_planner_backend.entities.Translation import Translation  # noqa: F401


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.lock = RLock()
        self.engine = create_engine(f'sqlite:///{self.data_dir / "cooking-planner.db"}',
                                    connect_args={'check_same_thread': False})
        event.listen(self.engine, 'connect', lambda dbapi, _: dbapi.execute('PRAGMA foreign_keys=ON'))
        with self.engine.begin() as connection:
            columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(ingredient_price)')}
            if columns and 'basis_quantity' not in columns:
                connection.exec_driver_sql('ALTER TABLE ingredient_price ADD COLUMN basis_quantity INTEGER')
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def session(self):
        with self.lock, self.sessions.begin() as session:
            yield session

    def marker_exists(self, name: str) -> bool:
        with self.session() as session:
            return session.get(Marker, name) is not None

    def close(self):
        self.engine.dispose()
