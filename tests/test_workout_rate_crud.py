"""
Test suite for workout_rate CRUD operations and business rules.
"""
import unittest
from fastapi import HTTPException
from app.core.database_connection import SessionLocal
from app.models.workout_rate_model import WorkoutRateModel
from app.schemas.workout_rate_schema import WorkoutRateCreate, WorkoutRateUpdate
from app.controllers import workout_rate_controller
from app.main import app


class TestWorkoutRateCRUD(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_openapi_schema(self):
        """Verifica que FastAPI genere el esquema OpenAPI con las nuevas rutas de workout-rates."""
        schema = app.openapi()
        paths = schema["paths"]
        self.assertIn("/workout-rates/", paths)
        self.assertIn("/workout-rates/{rate_id}", paths)
        self.assertIn("/workout-rates/upsert", paths)
        self.assertIn("/workout-rates/workout/{id_workout}/score", paths)
        self.assertIn("/workout-rates/workout/{id_workout}/user/{user_id}", paths)

    def test_pydantic_validation(self):
        """Valida que Pydantic rechace valores menores a 1 o mayores a 5."""
        with self.assertRaises(Exception):
            WorkoutRateCreate(id_workout=2, user_id=1, rate=0)
        with self.assertRaises(Exception):
            WorkoutRateCreate(id_workout=2, user_id=1, rate=6)

        valid_schema = WorkoutRateCreate(id_workout=2, user_id=1, rate=4)
        self.assertEqual(valid_schema.rate, 4)

    def test_get_workout_rates_list(self):
        """Prueba listado y filtros."""
        rates = workout_rate_controller.get_workout_rates(self.db, skip=0, limit=10)
        self.assertIsInstance(rates, list)
        self.assertGreaterEqual(len(rates), 1)

    def test_get_workout_score(self):
        """Prueba cálculo de puntuación para ejercicio público."""
        score = workout_rate_controller.get_workout_score(self.db, id_workout=2)
        self.assertEqual(score["id_workout"], 2)
        self.assertIn("avg_rate", score)
        self.assertIn("total_rates", score)
        self.assertGreater(score["total_rates"], 0)

    def test_reject_private_workout_rate(self):
        """Prueba que el trigger trg_workout_rate_check_public impida valorar un ejercicio privado (id=3)."""
        create_data = WorkoutRateCreate(id_workout=3, user_id=1, rate=5)
        with self.assertRaises(HTTPException) as ctx:
            workout_rate_controller.create_workout_rate(self.db, create_data)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("debe ser público y estar activo", ctx.exception.detail)

    def test_crud_lifecycle_and_upsert(self):
        """
        Ciclo de vida completo:
        1. Limpiar valoración previa del usuario 1 para ejercicio 2 si existiera.
        2. Crear valoración (POST).
        3. Consultar valoración por ID y por usuario/ejercicio (GET).
        4. Intentar duplicar y esperar HTTP 409 (UNIQUE).
        5. Actualizar valoración (PUT).
        6. Probar upsert.
        7. Eliminar valoración (DELETE).
        8. Comprobar 404 tras eliminación.
        """
        # 1. Limpieza inicial si existiese
        existing = self.db.query(WorkoutRateModel).filter(
            WorkoutRateModel.id_workout == 2,
            WorkoutRateModel.user_id == 1
        ).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()

        # 2. Crear nueva valoración
        new_rate = WorkoutRateCreate(id_workout=2, user_id=1, rate=4)
        created = workout_rate_controller.create_workout_rate(self.db, new_rate)
        self.assertIsNotNone(created.id)
        self.assertEqual(created.rate, 4)
        rate_id = created.id

        # 3. Consultar por ID
        fetched = workout_rate_controller.get_workout_rate_by_id(self.db, rate_id)
        self.assertEqual(fetched.id, rate_id)
        self.assertEqual(fetched.rate, 4)

        # Consultar por usuario y ejercicio
        fetched_by_user = workout_rate_controller.get_workout_rate_by_workout_and_user(self.db, id_workout=2, user_id=1)
        self.assertEqual(fetched_by_user.id, rate_id)

        # 4. Intentar crear duplicado -> 409 Conflict
        with self.assertRaises(HTTPException) as ctx:
            workout_rate_controller.create_workout_rate(self.db, new_rate)
        self.assertEqual(ctx.exception.status_code, 409)

        # 5. Actualizar puntuación
        update_data = WorkoutRateUpdate(rate=5)
        updated = workout_rate_controller.update_workout_rate(self.db, rate_id, update_data)
        self.assertEqual(updated.rate, 5)

        # 6. Upsert (actualiza a 3)
        upsert_data = WorkoutRateCreate(id_workout=2, user_id=1, rate=3)
        upserted = workout_rate_controller.upsert_workout_rate(self.db, upsert_data)
        self.assertEqual(upserted.id, rate_id)
        self.assertEqual(upserted.rate, 3)

        # 7. Eliminar
        workout_rate_controller.delete_workout_rate(self.db, rate_id)

        # 8. Comprobar que ya no existe -> 404 Not Found
        with self.assertRaises(HTTPException) as ctx:
            workout_rate_controller.get_workout_rate_by_id(self.db, rate_id)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
