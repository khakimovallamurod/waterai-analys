import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./waterai.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Mavjud jadvallarga keyinroq qo'shilgan ustunlar (yengil migratsiya)
_ADDED_COLUMNS = {
    "water_analyses": {
        "data_source": "VARCHAR(20) NOT NULL DEFAULT 'manual'",
        "salinity": "FLOAT",
        "orp": "FLOAT",
    },
}


def migrate_columns():
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
