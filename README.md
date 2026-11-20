# FastAPI Boilerplate

A simple boilerplate to quickly start a FastAPI project. Its main dependencies are FastAPI, SQLAlchemy, Alembic for database migrations, and Faker for sample data.

## Setup

1. Install main dependencies

```bash
pip install -r requirements.txt
cp .env.example .env
```

2. Edit the database settings in .env:

```python
DB_HOST: database server address
DB_PORT: database port
DB_NAME: database name
DB_USER: database user
DB_PASSWORD: database password
DRIVER_NAME: SQLAlchemy driver, for example postgresql+psycopg
```


## Migrations

1. Create a migration after changing your models:

``` 
alembic revision --autogenerate -m "describe your change"
```

2. Apply migrations:

```
alembic upgrade head
```

## Seed data

1. Run the seeder (50 records by default):

```
python -m seeders.run
```

2.Or Choose the number of records with --count:

```
python -m seeders.run --count 100
```

## Run the API
```
uvicorn app.main:app --reload
```