import argparse
from app.core.database_connection import SessionLocal
from seeders.test_seeder import seed
from seeders.workout_rate_seeder import seed_workout_rates


def main():
    parser = argparse.ArgumentParser(description="Poblador de base de datos para VolumeLab")
    parser.add_argument("--count", type=int, default=50, help="Número de registros de prueba (donde aplique)")
    parser.add_argument(
        "--entity",
        type=str,
        default="all",
        choices=["test", "workout_rate", "all"],
        help="Entidad a poblar",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.entity in ["test", "all"]:
            seed(db, args.count)
            print(f"Seeded {args.count} records for test")
        if args.entity in ["workout_rate", "all"]:
            count_rates = seed_workout_rates(db)
            print(f"Seeded {count_rates} records for workout_rate")
    finally:
        db.close()


if __name__ == "__main__":
    main()
