import argparse
from app.core.database_connection import SessionLocal
from seeders.test_seeder import seed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed(db, args.count)
        print(f"Seeded {args.count} records")
    finally:
        db.close()

if __name__ == "__main__":
    main()