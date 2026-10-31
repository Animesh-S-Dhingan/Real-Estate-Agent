"""CLI: python -m scripts.seed_data"""

from app.core.database import Base, SessionLocal, engine
from app.seed import seed_all, seed_if_empty


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_all(db)
        print("Seed complete:", result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
