# VolumeLab — Backend API

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-6BA81E)](https://alembic.sqlalchemy.org/)
[![Modelo de Datos](https://img.shields.io/badge/Esquema_BD-v4_(20--11--2026)-16a34a)](#modelo-de-datos)
[![RGPD](https://img.shields.io/badge/RGPD-Art._17_Derecho_de_Supresi%C3%B3n-2563eb)](#cumplimiento-rgpd-y-auditor%C3%ADa)

API REST y capa de negocio del proyecto **VolumeLab** (Proyecto Deloitte), construida con **Python**, **FastAPI**, **PostgreSQL** y **Alembic**: plataforma de registro, planificación y análisis cuantitativo de entrenamiento de fuerza e hipertrofia.

Este repositorio centraliza la autenticación y autorización por roles, la gestión del catálogo de ejercicios y grupos musculares, la planificación por mesociclos y semanas, el registro granular de series (`1 fila = 1 serie`), el motor de cálculo automático de métricas de entrenamiento, las valoraciones comunitarias, la exportación de datos (CSV/Excel), la auditoría y el cumplimiento del RGPD.

---

## Tabla de contenidos

1. [Resumen del dominio](#resumen-del-dominio)
2. [Stack tecnológico](#stack-tecnol%C3%B3gico)
3. [Roles y matriz de permisos](#roles-y-matriz-de-permisos)
4. [Requisitos funcionales (RF-01 a RF-17)](#requisitos-funcionales-rf-01-a-rf-17)
5. [Reglas de negocio (RN-01 a RN-19)](#reglas-de-negocio-rn-01-a-rn-19)
6. [Motor de cálculo y responsabilidades del backend](#motor-de-c%C3%A1lculo-y-responsabilidades-del-backend)
7. [Modelo de datos](#modelo-de-datos)
   - [Diagrama Entidad-Relación](#diagrama-entidad-relaci%C3%B3n)
   - [Tipos enumerados (ENUM)](#tipos-enumerados-enum)
   - [Tablas principales](#tablas-principales)
   - [Vistas SQL](#vistas-sql)
   - [Triggers de integridad y negocio](#triggers-de-integridad-y-negocio)
8. [Cumplimiento RGPD y auditoría](#cumplimiento-rgpd-y-auditor%C3%ADa)
9. [Estructura recomendada del repositorio](#estructura-recomendada-del-repositorio)
10. [Instalación, migraciones y ejecución local](#instalaci%C3%B3n-migraciones-y-ejecuci%C3%B3n-local)
11. [Equipo](#equipo)

---

## Resumen del dominio

**VolumeLab** permite a los usuarios planificar bloques de entrenamiento (*mesociclos* divididos en *semanas*), registrar sesiones con precisión serie a serie (tanto para ejercicios dinámicos como isométricos) y analizar su progresión real separando estrictamente **volumen**, **intensidad** y **series semanales ponderadas por grupo muscular**.

Principios clave del diseño backend:

- **Modelo v4 (`1 fila de workout_set = 1 serie`):** cada serie individual almacena sus datos de ejecución y sus métricas calculadas (`effective_weight_kg`, `one_rm_kg`, `one_rm_percentage`, `volume_load`).
- **Integridad histórica:** las sesiones almacenan una instantánea del peso corporal vigente en la fecha del entrenamiento (`current_bodyweight_kg`), los ejercicios usados nunca se borran físicamente y las sesiones cerradas quedan bloqueadas frente a ediciones.
- **Récords y puntuaciones siempre consistentes:** ni los récords personales (*PR*) ni las medias de valoración se guardan en columnas redundantes; se calculan dinámicamente mediante vistas SQL.
- **Defensa en profundidad:** las validaciones de entrada y negocio se aplican en **Pydantic / servicios FastAPI** y se refuerzan a nivel de **PostgreSQL** (`CHECK`, `UNIQUE`, `DEFERRABLE`, `FOR UPDATE` y triggers PL/pgSQL).

---

## Stack tecnológico

| Capa | Tecnología | Rol |
| --- | --- | --- |
| **Lenguaje** | Python 3.11+ | Runtime principal del backend |
| **Framework API** | FastAPI + Uvicorn | Endpoints REST, inyección de dependencias y documentación OpenAPI (`/docs`, `/redoc`) |
| **Validación / Serialización** | Pydantic v2 | Validación de esquemas de entrada/salida y configuración (`pydantic-settings`) |
| **Base de datos** | PostgreSQL 14+ | Persistencia relacional (`UTF8`, `LC_CTYPE = 'es-ES'`), `ENUM`, vistas y triggers PL/pgSQL |
| **ORM / Driver** | SQLAlchemy 2.x + `psycopg` / `asyncpg` | Mapeo relacional, consultas analíticas y gestión de transacciones |
| **Migraciones** | Alembic | Versionado reproducible del esquema, tipos `ENUM`, vistas y triggers |
| **Exportación** | CSV (`csv`) / Excel (`openpyxl` o `pandas`) | Exportación de registros y analíticas con trazabilidad en `audit` (**RF-15**) |
| **Testing** | `pytest` + `httpx` | Pruebas unitarias y de integración contra PostgreSQL |

---

## Roles y matriz de permisos

El sistema gestiona dos roles definidos mediante `role_user ('ADMIN', 'CLIENTE')`:

| Capacidad / Recurso | `ADMIN` | `CLIENTE` |
| --- | :---: | :---: |
| Gestión de cuentas, roles y estado (`ACTIVO` / `BLOQUEADO`) | Sí | Solo su propio perfil |
| Gestión de perfil biométrico e histórico de peso (`weight_history`) | Consulta global y gestión | Propio |
| Creación y mantenimiento de grupos musculares (`muscle_group`) | **Sí (exclusivo)** | No |
| Creación de ejercicios privados (`workout`, `public = FALSE`) | Sin límite | Sin límite |
| Creación / publicación de ejercicios públicos (`workout`, `public = TRUE`) | Sin límite | **Máximo 20 públicos** |
| Desactivación lógica de ejercicios (`state = FALSE`) | Sí | Según propiedad/política |
| Parametrización de fórmulas (1RM, isométricos) y rangos de validación | Sí | No |
| Planificación de mesociclos y semanas (`mesocycle`, `training_week`) | Supervisión global | Propios |
| Creación de sesiones privadas (`workout_session`, `public = FALSE`) | Sin límite | Sin límite |
| Creación / publicación de sesiones públicas (`workout_session`, `public = TRUE`) | Sin límite | **Máximo 20 públicas** |
| Registro, edición y reordenación de series (`workout_set`) | Supervisión | Propias (si sesión `ABIERTO`) |
| Valoración (1–5) de sesiones públicas y ejercicios públicos activos | Sí | Sí (1 voto actualizable por recurso) |
| Analítica individual y récords personales | Propia y global | Propia |
| Estadísticas agregadas globales | Sí | No |
| Exportación (CSV / Excel) con registro en `audit` (`EXPORT`) | Sí | Propia |
| Consulta de auditoría y gestión de seguridad | Sí | No |

---

## Requisitos funcionales (RF-01 a RF-17)

### Autenticación, Usuarios y Perfiles

| ID | Requisito | Descripción |
| --- | --- | --- |
| **RF-01** | Autenticación y aislamiento de datos | Inicio de sesión seguro con email único insensible a mayúsculas/minúsculas. Aislamiento estricto: cada `CLIENTE` accede solo a sus datos privados y a ejercicios/sesiones marcados como `public = TRUE`. |
| **RF-02** | Gestión administrativa de usuarios | El `ADMIN` puede crear, editar, bloquear (`BLOQUEADO`) o eliminar cuentas, además de gestionar credenciales y roles (`ADMIN`, `CLIENTE`). |
| **RF-03** | Perfil e histórico de peso | El `CLIENTE` registra y actualiza altura, fecha de nacimiento, género y peso corporal. Cada actualización de peso genera una entrada fechada en `weight_history`, consultable por el usuario y el administrador. |

### Catálogo de Ejercicios, Músculos y Parametrización

| ID | Requisito | Descripción |
| --- | --- | --- |
| **RF-04** | Gestión del catálogo de ejercicios | Alta de ejercicios indicando nombre, descripción, tipo (`DINAMICO` / `ISOMETRICO`), uso de peso corporal (`is_bodyweight`), lastre positivo, lastre negativo/asistencia y visibilidad (`public`). `ADMIN` sin límite; `CLIENTE` ilimitado privado y máx. 20 públicos. Solo `ADMIN` crea grupos musculares. |
| **RF-05** | Prevención de duplicados y desactivación lógica | Impide nombres duplicados en `workout` y `muscle_group`. Permite desactivar ejercicios (`state = FALSE`) preservando intacto el historial de entrenamientos. |
| **RF-06** | Asignación muscular ponderada | Asociación `N:M` entre ejercicios y grupos musculares (`muscle_workout`) con rol y ponderación fija: `PRIMARIO` (`100` / ×1,0), `SECUNDARIO` (`50` / ×0,5) y `TERCIARIO` (`10` / ×0,1). |
| **RF-07** | Parametrización de fórmulas y validaciones | El `ADMIN` define y documenta la fórmula de estimación de 1RM (en función de peso, repeticiones y RIR), reglas para isométricos y límites mínimos/máximos de peso, repeticiones, RIR, duración y asistencia. |

### Planificación, Registro de Entrenamientos y Comunidad

| ID | Requisito | Descripción |
| --- | --- | --- |
| **RF-08** | Gestión de mesociclos y semanas | Creación y mantenimiento de mesociclos (`PLANIFICADO`, `ACTIVO`, `FINALIZADO`) y semanas numeradas (`week_order`) para comparar periodos de entrenamiento. |
| **RF-09** | Gestión y reutilización de sesiones | Alta de sesiones de entrenamiento (privadas sin límite; `CLIENTE` máx. 20 públicas), duplicación de sesiones previas y reutilización de ejercicios recientes. |
| **RF-10** | Registro y edición de series | Inserción, edición, reordenación y borrado de series individuales en `workout_set` mientras la sesión esté en estado `ABIERTO`: dinámicas (`added_weight_kg`, `reps`, `rir`, `note`) e isométricas (`duration_second`, carga/asistencia, `rir`, `note`). |
| **RF-11** | Alertas y validaciones | Validación en FastAPI/Pydantic y PostgreSQL para rechazar datos incompletos o incoherentes y emitir alertas ante cambios bruscos de carga respecto al historial del usuario. |
| **RF-17** | Valoraciones públicas | Puntuación de 1 a 5 (un voto actualizable por usuario) sobre sesiones públicas (`session_rate`) y ejercicios públicos activos (`workout_rate`), exponiendo media y recuento vía `v_session_score` y `v_workout_score`. |

### Motor de Cálculo, Analítica, Exportación, Auditoría y RGPD

| ID | Requisito | Descripción |
| --- | --- | --- |
| **RF-12** | Cálculo automático de métricas por serie | Al crear/actualizar una serie, el backend calcula `effective_weight_kg`, `one_rm_kg` (dinámicos), `one_rm_percentage` (dinámicos), `volume_load` y la distribución de series y volumen ponderado por músculo. |
| **RF-13** | Analítica y progresión del usuario | Endpoints de evolución de 1RM, carga/lastre, reps, RIR y volumen; historial y PR vigente (`v_personal_record_history`, `v_current_personal_record`); histórico de sesiones; comparativa semanal de volumen por músculo y distribución por mesociclo, filtrables por fecha, ejercicio, músculo, sesión, semana y mesociclo. |
| **RF-14** | Estadísticas globales (`ADMIN`) | Métricas globales agregadas filtrables por ejercicio, músculo, usuario, semana y mesociclo. |
| **RF-15** | Exportación de datos | Exportación de registros y analíticas a **CSV** y **Excel**, registrando el evento `EXPORT` en `audit`. |
| **RF-16** | Trazabilidad, seguridad y RGPD | Log de auditoría (`INSERT`, `UPDATE`, `DELETE`, `EXPORT`), control de acceso, copias de seguridad y derecho de supresión (RGPD art. 17) eliminando en cascada todos los datos personales del usuario sin romper el catálogo compartido. |

---

## Reglas de negocio (RN-01 a RN-19)

| ID | Regla | Descripción resumida | Nivel de control |
| --- | --- | --- | --- |
| **RN-01** | Peso corporal histórico | Todo cálculo dependiente del peso corporal usa la instantánea vigente en `session_date` (`workout_session.current_bodyweight_kg > 0`), sin recalcular sesiones pasadas ante cambios posteriores. | Backend + `CHECK` |
| **RN-02** | Peso total movilizado | Si `is_bodyweight = TRUE`, `effective_weight_kg = current_bodyweight_kg + added_weight_kg` (sumando lastre positivo si `allow_positive_ballast` o restando asistencia si `allow_negative_ballast`). Si `is_bodyweight = FALSE`, equivale a `added_weight_kg`. | Backend |
| **RN-03** | Carga de volumen y ponderación muscular | Dinámicos: `volume_load = effective_weight_kg * reps`. Series y volumen se ponderan por músculo con `weighing`: `100` (`PRIMARIO`), `50` (`SECUNDARIO`), `10` (`TERCIARIO`). | Backend + `CHECK` |
| **RN-04** | Dinámicos vs. Isométricos | `DINAMICO` exige `reps` para 1RM, %1RM y `volume_load`; `ISOMETRICO` usa `duration_second` con reglas parametrizadas por `ADMIN`. | Backend + Trigger |
| **RN-05** | Separación de dimensiones analíticas | Mantener estrictamente separadas las métricas de **volumen**, **intensidad** (%1RM / RIR) y **series semanales por músculo**, sin fusionarlas en una métrica compuesta. | Backend (API / Servicios) |
| **RN-06** | Integridad del catálogo e historial | `workout.name` único. No se puede eliminar físicamente un ejercicio con series registradas (`ON DELETE RESTRICT`); debe desactivarse con `state = FALSE`. | BD (`UNIQUE`, `FK`) + Backend |
| **RN-07** | Bloqueo por cierre de sesión | Solo se pueden insertar, editar o borrar filas de `workout_set` cuando `workout_session.status = 'ABIERTO'`. Además `closed_at IS NOT NULL` ⇔ `status = 'CERRADO'`. No bloquea borrados en cascada. | BD (Trigger + `CHECK`) + Backend |
| **RN-08** | Límites paramétricos y de dominio | `birth_date <= CURRENT_DATE`; `height_cm` entre `50` y `300`; `weight_kg > 0`; `current_bodyweight_kg > 0`; `exercise_order >= 1`; `set_number >= 1`; `reps >= 1`; `duration_second >= 1`; `rir` entre `0` y `10`; `effective_weight_kg > 0`; `one_rm_percentage >= 0`, más límites configurados por `ADMIN`. | BD (`CHECK`) + Pydantic/Backend |
| **RN-09** | Exclusión mutua `reps` / `duration_second` | Una serie debe informar exactamente uno de los dos campos, nunca ambos ni ninguno: `(reps IS NULL) <> (duration_second IS NULL)`. | BD (`CHECK`) + Pydantic |
| **RN-10** | Duración obligatoria en isométricos | Si el ejercicio es `ISOMETRICO`, `duration_second` es obligatorio. | BD (Trigger) + Backend |
| **RN-11** | Unicidad de posición y orden coherente | `UNIQUE (session_id, exercise_order, set_number) DEFERRABLE INITIALLY IMMEDIATE` (permite intercambiar órdenes en un único `UPDATE`) y cada `exercise_order` de una sesión solo admite un único `exercise_id`. | BD (`UNIQUE` + Trigger `AFTER`) |
| **RN-12** | Exclusión de 1RM en isométricos | En ejercicios `ISOMETRICO`, `one_rm_kg` y `one_rm_percentage` deben ser siempre `NULL`. | BD (Trigger) + Backend |
| **RN-13** | Cálculo dinámico de récords personales (PR) | Sin columna booleana persistida: calculado por usuario y ejercicio en orden `(session_date, session_id, exercise_order, set_number, id)` mediante vistas. Es PR si supera estrictamente (`>`) el máximo `volume_load` previo (empatar no es PR; la primera serie sí). | BD (Vistas SQL) |
| **RN-14** | Email único insensible a mayúsculas | No pueden coexistir dos usuarios con el mismo email independientemente de mayúsculas/minúsculas (`UNIQUE INDEX` sobre `LOWER(email)`). | BD (Índice único) + Backend |
| **RN-15** | Coherencia de asistencia | `allow_negative_ballast = TRUE` exige obligatoriamente `is_bodyweight = TRUE`. | BD (`CHECK`) + Pydantic |
| **RN-16** | Coherencia temporal y conservación de sesiones | `end_date >= start_date` en `mesocycle` y `training_week`; `week_order >= 1` único por mesociclo. Borrar una semana o mesociclo conserva las sesiones con `week_id = NULL`. | BD (`CHECK`, `UNIQUE`, `FK`) |
| **RN-17** | Permisos y límites por rol | Solo `ADMIN` crea `muscle_group`. `CLIENTE`: máx. 20 `workout` públicos y máx. 20 `workout_session` públicas (privados sin límite). `ADMIN` sin límite. Control concurrente mediante `SELECT ... FOR UPDATE` sobre `app_user`. | BD (Triggers) + FastAPI Deps |
| **RN-18** | Valoraciones públicas | `rate` entero entre `1` y `5`; 1 voto por usuario y recurso (`UNIQUE`, actualizable vía `UPDATE`). Solo sesiones `public = TRUE` y ejercicios `public = TRUE AND state = TRUE`. Medias calculadas en vistas. | BD (`CHECK`, `UNIQUE`, Triggers, Vistas) |
| **RN-19** | Derecho de supresión (RGPD, art. 17) | `DELETE FROM app_user` elimina en cascada `weight_history`, `mesocycle`, `training_week`, `workout_session`, `workout_set`, `session_rate`, `workout_rate` y `audit`; conserva `workout` y `muscle_group` con `created_by = NULL`. | BD (`ON DELETE CASCADE` / `SET NULL`) |

---

## Motor de cálculo y responsabilidades del backend

### Campos calculados por la capa de servicios

Al crear o modificar sesiones y series, los servicios de FastAPI deben calcular y persistir los siguientes valores dentro de la misma transacción:

1. **Instantánea de peso corporal (`workout_session.current_bodyweight_kg`):**
   - Consultar en `weight_history` el registro más reciente del usuario con `created_at <= session_date` (aprovechando `idx_weight_history_user_date`) y fijarlo en la sesión (**RN-01**).

2. **Peso efectivo (`workout_set.effective_weight_kg`):**
   - Si `workout.is_bodyweight = TRUE`:
     $$\text{effective\_weight\_kg} = \text{current\_bodyweight\_kg} + \text{added\_weight\_kg}$$
     validando que `added_weight_kg > 0` solo se permita si `allow_positive_ballast = TRUE`, que `added_weight_kg < 0` solo se permita si `allow_negative_ballast = TRUE`, y que el resultado sea estrictamente `> 0` (**RN-02**, **RN-08**).
   - Si `workout.is_bodyweight = FALSE`:
     $$\text{effective\_weight\_kg} = \text{added\_weight\_kg}$$

3. **Carga de volumen de la serie (`workout_set.volume_load`):**
   - **Ejercicio `DINAMICO`:**
     $$\text{volume\_load} = \text{effective\_weight\_kg} \times \text{reps}$$
   - **Ejercicio `ISOMETRICO`:**
     $$\text{volume\_load} = \text{effective\_weight\_kg} \times \text{duration\_second} \quad (\text{cuando aplique según parametrización})$$

4. **Estimación de 1RM e intensidad relativa (`one_rm_kg`, `one_rm_percentage`):**
   - **Ejercicio `DINAMICO`:** aplicar la fórmula parametrizada por el administrador (**RF-07**) a partir de `effective_weight_kg`, `reps` y `rir`, y calcular `%1RM = (effective_weight_kg / one_rm_kg) * 100`.
   - **Ejercicio `ISOMETRICO`:** asignar explícitamente `one_rm_kg = None` y `one_rm_percentage = None` (**RN-12**).

5. **Distribución muscular ponderada (en consultas analíticas):**
   - Para cada músculo asociado en `muscle_workout`:
     - **Series ponderadas:** $1 \times (\text{weighing} / 100)$
     - **Volumen ponderado:** $\text{volume\_load} \times (\text{weighing} / 100)$
   - Devolver siempre **volumen**, **intensidad** y **series semanales** como dimensiones separadas (**RN-05**).

### Notas de implementación en FastAPI + SQLAlchemy + Alembic

- **Reordenación de ejercicios en una sesión:** la restricción `uq_workout_set_position` es `DEFERRABLE INITIALLY IMMEDIATE` y el trigger `trg_workout_set_order_exercise` es `AFTER`. El backend puede intercambiar `exercise_order` de dos ejercicios en una única sentencia `UPDATE` con `CASE` (sin colisiones intermedias).
- **Mapeo de excepciones de PostgreSQL a HTTP:** capturar `IntegrityError` y `DBAPIError` (incluidas las excepciones `RaiseException` lanzadas por triggers PL/pgSQL) en un exception handler global de FastAPI:
  - `RN-07` (sesión cerrada), `RN-06` (`ON DELETE RESTRICT` o `name` duplicado), `RN-14` (email duplicado) → `409 Conflict`.
  - `RN-17` (solo `ADMIN` en `muscle_group` o cuota de 20 públicos superada por `CLIENTE`) → `403 Forbidden` (rol) / `422 Unprocessable Entity` (cuota).
  - Violaciones de `CHECK` o triggers de coherencia (`RN-04`, `RN-08`, `RN-09`, `RN-10`, `RN-12`, `RN-15`, `RN-18`) → `422 Unprocessable Entity`.
- **Concurrencia en cuotas de `CLIENTE`:** los triggers de límite bloquean la fila del usuario en `app_user` con `SELECT ... FOR UPDATE`; mantener las transacciones breves al publicar ejercicios o sesiones.
- **Migraciones con Alembic:** `alembic revision --autogenerate` no detecta automáticamente vistas SQL (`CREATE VIEW`) ni funciones/triggers PL/pgSQL (`CREATE FUNCTION`, `CREATE TRIGGER`). Gestionar dichos objetos en migraciones explícitas con `op.execute(...)` (tanto en `upgrade()` como en `downgrade()`), tomando `volumelab_20-11-2026_v4.sql` como referencia canónica del esquema v4.

---

## Modelo de datos

Versión del esquema: **`v4` (20/11/2026)** — **12 tablas**, **16 relaciones**, **8 tipos `ENUM`**, **4 vistas SQL** y **8 triggers**.

### Diagrama Entidad-Relación

```mermaid
erDiagram
    app_user ||--o{ weight_history : "registra"
    app_user ||--o{ mesocycle : "planifica"
    app_user ||--o{ workout_session : "realiza"
    app_user ||--o{ session_rate : "valora"
    app_user ||--o{ workout_rate : "valora"
    app_user ||--o{ audit : "genera"
    app_user |o--o{ workout : "crea (SET NULL)"
    app_user |o--o{ muscle_group : "crea ADMIN (SET NULL)"

    mesocycle ||--o{ training_week : "contiene"
    training_week |o--o{ workout_session : "agrupa (SET NULL)"

    workout_session ||--o{ workout_set : "compone"
    workout_session ||--o{ session_rate : "recibe"

    workout ||--o{ workout_set : "se ejecuta en (RESTRICT)"
    workout ||--|{ muscle_workout : "implica"
    workout ||--o{ workout_rate : "recibe"

    muscle_group ||--o{ muscle_workout : "participa en"
```

> El diagrama ER visual interactivo se mantiene además en `VolumeLab — Diagrama Entidad-Relación.html`.

### Tipos enumerados (`ENUM`)

| Tipo SQL | Valores | Columna |
| --- | --- | --- |
| `user_gender` | `HOMBRE`, `MUJER`, `PREFIERO NO DECIR` | `app_user.gender` |
| `user_status` | `ACTIVO`, `BLOQUEADO` | `app_user.status` |
| `role_user` | `ADMIN`, `CLIENTE` | `app_user.role` |
| `exercise_type` | `DINAMICO`, `ISOMETRICO` | `workout.type` |
| `muscle_role` | `PRIMARIO`, `SECUNDARIO`, `TERCIARIO` | `muscle_workout.role_muscular` |
| `mesocycle_status` | `PLANIFICADO`, `ACTIVO`, `FINALIZADO` | `mesocycle.status` |
| `session_status` | `ABIERTO`, `CERRADO` | `workout_session.status` |
| `audit_action` | `INSERT`, `UPDATE`, `DELETE`, `EXPORT` | `audit.action` |

### Tablas principales

| Módulo | Tabla | Propósito y claves clave |
| --- | --- | --- |
| **Usuarios** | `app_user` | Cuentas, credenciales (`password_hash`), rol, estado y perfil base. Índice único `LOWER(email)`. |
| **Usuarios** | `weight_history` | Histórico cronológico de peso corporal (`weight_kg > 0`). Índice `(user_id, created_at DESC)`. |
| **Catálogo** | `muscle_group` | Catálogo maestro de grupos musculares (`name` único; creación exclusiva `ADMIN`). |
| **Catálogo** | `workout` | Catálogo de ejercicios (`name` único, tipo, flags de peso corporal/lastre, `public`, `state`). |
| **Catálogo** | `muscle_workout` | Relación `N:M` ejercicio-músculo con `role_muscular` y `weighing` (`100` / `50` / `10`). |
| **Planificación** | `mesocycle` | Bloques macro de entrenamiento con rango de fechas y `status`. |
| **Planificación** | `training_week` | Semanas numeradas (`week_order >= 1`, único por mesociclo) dentro de un mesociclo. |
| **Entrenamiento** | `workout_session` | Sesiones de entrenamiento con `session_date`, snapshot `current_bodyweight_kg`, `public`, `status` y `closed_at`. |
| **Entrenamiento** | `workout_set` | **1 fila = 1 serie.** Orden `(exercise_order, set_number)`, datos de ejecución y campos calculados (`effective_weight_kg`, `one_rm_kg`, `one_rm_percentage`, `volume_load`). |
| **Valoraciones** | `session_rate` | Puntuación `1..5` por usuario sobre sesiones públicas (`UNIQUE (id_workout_session, user_id)`). |
| **Valoraciones** | `workout_rate` | Puntuación `1..5` por usuario sobre ejercicios públicos activos (`UNIQUE (id_workout, user_id)`). |
| **Auditoría** | `audit` | Trazabilidad de acciones (`INSERT`, `UPDATE`, `DELETE`, `EXPORT`) con `entity`, `record_id`, `endpoint` y `created_at`. |

### Vistas SQL

| Vista | Columnas expuestas | Propósito |
| --- | --- | --- |
| `v_session_score` | `id_workout_session`, `avg_rate`, `total_rates` | Nota media (`ROUND(AVG(rate), 2)`) y total de votos por sesión. |
| `v_workout_score` | `id_workout`, `avg_rate`, `total_rates` | Nota media (`ROUND(AVG(rate), 2)`) y total de votos por ejercicio. |
| `v_personal_record_history` | `set_id`, `user_id`, `exercise_id`, `session_id`, `session_date`, `volume_load`, `previous_best` | Historial cronológico de cada serie que superó estrictamente la mejor marca previa del usuario en ese ejercicio (**RN-13**). |
| `v_current_personal_record` | `set_id`, `user_id`, `exercise_id`, `session_id`, `session_date`, `volume_load` | Récord personal vigente por usuario y ejercicio (**RN-13**). |

### Triggers de integridad y negocio

| Trigger | Tabla / Evento | Función y regla garantizada |
| --- | --- | --- |
| `trg_workout_set_check_type` | `workout_set` (`BEFORE INSERT/UPDATE`) | `ISOMETRICO` exige `duration_second` y prohíbe `one_rm_kg` / `one_rm_percentage`; `DINAMICO` exige `reps` (**RN-04**, **RN-10**, **RN-12**). |
| `trg_workout_set_session_open` | `workout_set` (`BEFORE INSERT/UPDATE/DELETE`) | Bloquea modificaciones sobre series de sesiones en estado `CERRADO`, sin interferir en borrados en cascada (**RN-07**). |
| `trg_workout_set_order_exercise` | `workout_set` (`AFTER INSERT/UPDATE`) | Garantiza que cada `exercise_order` dentro de una sesión corresponda a un único `exercise_id` (**RN-11**). |
| `trg_session_rate_check_public` | `session_rate` (`BEFORE INSERT/UPDATE`) | Solo permite valorar sesiones con `public = TRUE` (**RN-18**). |
| `trg_workout_rate_check_public` | `workout_rate` (`BEFORE INSERT/UPDATE`) | Solo permite valorar ejercicios con `public = TRUE` y `state = TRUE` (**RN-18**). |
| `trg_muscle_group_admin_only` | `muscle_group` (`BEFORE INSERT/UPDATE OF created_by`) | Exige `created_by` con rol `ADMIN` en `INSERT`; admite `NULL` en `UPDATE` para `ON DELETE SET NULL` (**RN-17**, **RN-19**). |
| `trg_workout_client_limit` | `workout` (`BEFORE INSERT/UPDATE OF created_by, public`) | Limita a 20 ejercicios públicos por `CLIENTE` con bloqueo `FOR UPDATE` (**RN-17**). |
| `trg_session_client_limit` | `workout_session` (`BEFORE INSERT/UPDATE OF user_id, public`) | Limita a 20 sesiones públicas por `CLIENTE` con bloqueo `FOR UPDATE` (**RN-17**). |

---

## Cumplimiento RGPD y auditoría

- **Derecho de supresión (RGPD, art. 17 — RN-19):**
  Al ejecutar `DELETE FROM app_user WHERE id = <user_id>`:
  - **Eliminación en cascada (`ON DELETE CASCADE`):** `weight_history`, `mesocycle` → `training_week`, `workout_session` → `workout_set`, `session_rate`, `workout_rate` y `audit`.
  - **Anonimización del catálogo compartido (`ON DELETE SET NULL`):** las filas creadas por el usuario en `workout` y `muscle_group` se conservan con `created_by = NULL` para evitar fallos de integridad referencial (`ON DELETE RESTRICT`) cuando otros usuarios tienen series registradas con dichos ejercicios.
- **Trazabilidad (`audit` — RF-15, RF-16):**
  El backend debe registrar toda operación crítica (`INSERT`, `UPDATE`, `DELETE`) y toda exportación de datos (`EXPORT`) indicando `user_id`, `entity`, `record_id`, `action` y `endpoint`.

---

## Estructura recomendada del repositorio

```text
volumelab-backend/
├── alembic/
│   ├── versions/               # Migraciones (tablas, ENUMs, vistas SQL y triggers PL/pgSQL)
│   └── env.py
├── app/
│   ├── api/                    # Routers FastAPI y dependencias (auth, roles, DB session)
│   ├── core/                   # Configuración (.env), seguridad (JWT/hashing), handlers de error
│   ├── db/                     # Engine/Session de SQLAlchemy y Base declarativa
│   ├── models/                 # Modelos ORM (app_user, workout, workout_session, workout_set...)
│   ├── schemas/                # Esquemas Pydantic v2 (request/response y validaciones RN-08/09/15)
│   ├── services/               # Lógica de negocio, motor de cálculo (1RM, volumen, PRs), exportación y auditoría
│   └── main.py                 # Punto de entrada de la aplicación FastAPI
├── db/
│   └── volumelab_20-11-2026_v4.sql   # Script SQL de referencia del esquema v4
├── tests/                      # Tests unitarios y de integración (pytest)
├── alembic.ini
├── requirements.txt            # o pyproject.toml
├── .env.example
└── README.md
```

---

## Instalación, migraciones y ejecución local

### 1. Requisitos previos

- **Python 3.11+**
- **PostgreSQL 14+** con soporte `UTF8` y locale `es-ES` (`LC_CTYPE = 'es-ES'`)

### 2. Clonar el repositorio y crear el entorno virtual

```bash
git clone <URL_DEL_REPOSITORIO_BACKEND>
cd volumelab-backend

python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Variables de entorno

Copia `.env.example` a `.env` y ajusta las credenciales de tu entorno local:

```env
# PostgreSQL
DATABASE_URL=postgresql+psycopg://postgres:changeme@localhost:5432/volumelab

# Seguridad / JWT
SECRET_KEY=changeme-use-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Aplicación
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 4. Inicialización de la base de datos y migraciones (Alembic)

**Opción A — Migraciones con Alembic (flujo habitual de desarrollo y despliegue):**

```bash
# Crear la base de datos vacía si aún no existe (UTF8 / es-ES)
psql -U postgres -d postgres -c "CREATE DATABASE volumelab ENCODING 'UTF8' LC_CTYPE = 'es-ES';"

# Aplicar todas las migraciones hasta la última revisión
alembic upgrade head
```

**Opción B — Carga directa del script SQL canónico v4 (entornos locales limpios):**

```bash
psql -U postgres -d postgres -f db/volumelab_20-11-2026_v4.sql
```

> **Advertencia:** `volumelab_20-11-2026_v4.sql` ejecuta `DROP DATABASE IF EXISTS volumelab;`. No utilizar directamente sobre entornos con datos persistentes sin respaldo previo.

Comandos útiles de Alembic:

```bash
# Generar una nueva migración tras modificar modelos SQLAlchemy
alembic revision --autogenerate -m "descripcion_del_cambio"

# Crear una migración manual (recomendado para cambios en vistas SQL o triggers PL/pgSQL)
alembic revision -m "actualizar_triggers_o_vistas"

# Consultar el estado actual de migraciones
alembic current

# Revertir la última migración
alembic downgrade -1
```

### 5. Arrancar el servidor de desarrollo

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación interactiva disponible una vez arrancado el servicio:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### 6. Ejecutar pruebas

```bash
pytest
```

---

## CRUD de grupos musculares (`muscle_group`)

La API incorpora las siguientes operaciones, documentadas también en `/docs`:

| Método | Ruta | Resultado |
| --- | --- | --- |
| POST | `/muscle-groups/` | Crea un grupo y devuelve `201` |
| GET | `/muscle-groups/` | Lista grupos con respuesta `200` |
| GET | `/muscle-groups/{muscle_group_id}` | Consulta un grupo o devuelve `404` |
| PUT | `/muscle-groups/{muscle_group_id}` | Actualiza los campos enviados |
| DELETE | `/muscle-groups/{muscle_group_id}` | Elimina un grupo sin asociaciones con respuesta `204` |

La creación requiere `name` y `created_by`. El nombre se recorta en sus extremos,
debe tener contenido y no superar 150 caracteres. Su unicidad conserva la
comparación existente de PostgreSQL. `description` es opcional y puede limpiarse
con `null`. Los campos omitidos en `PUT` conservan sus valores.

El creador debe existir y tener rol `ADMIN`; un cliente recibe `403` y un creador
inexistente recibe `404`. La reasignación del creador aplica la misma regla.
Eliminar al usuario creador conserva el grupo con `created_by=null`.
La autenticación del solicitante y sus permisos de edición y borrado se
integrarán con la tarea de autenticación común; validar el creador no autentica
al usuario que realiza la petición.

El listado acepta `skip`, `limit` (entre 1 y 500) y `created_by`, y se ordena por
identificador ascendente. `DELETE` devuelve `409` si existen asociaciones en
`muscle_workout`, conservando el grupo y sus enlaces. El borrado de grupos sin
asociaciones es físico: una consulta posterior devuelve `404`. No se añade un
campo `state` ni se modifica la cascada existente de PostgreSQL.

### Migración de grupos musculares

La revisión `d3c8a51f9072`, con etiqueta `muscle_group`, depende de
`ad8c21f5e9b7` (`app_user`). Crea los objetos ausentes o verifica y conserva una
tabla existente compatible, incluidas sus restricciones y el trigger de
administrador. No copia ni modifica la migración de `workout`.

Antes de crear o aplicar migraciones, avisar al equipo, actualizar la rama y
fusionar `origin/dev`. El comando de esta entidad es:

```bash
./env/Scripts/python.exe -m alembic upgrade muscle_group@head
```

La aplicación a la base local `volumelab` queda pendiente: esta ya registra la
revisión `f2a7c8e9d410` de `workout`, todavía ausente en `dev` al preparar este
cambio. Después de integrar esa tarea, actualizar la rama, conservar ambos
modelos y utilidades de pruebas, verificar el historial y aplicar la nueva
revisión. No eliminar revisiones registradas ni utilizar `stamp` para ocultar
esta dependencia. Las pruebas de esta entidad no necesitan la migración de
`workout` y utilizan bases desechables independientes.

La reversión elimina los objetos de `muscle_group`; se comprueba en bases
temporales y no debe ejecutarse para deshacer la adopción de datos de trabajo.

### Pruebas de grupos musculares

Desde la carpeta del backend:

```bash
./env/Scripts/python.exe -m pytest --ignore=tests/test_workout_rate_crud.py -q
./env/Scripts/python.exe -m pytest --ignore=tests/test_workout_rate_crud.py --run-postgres -q
```

La primera ejecución omite las pruebas PostgreSQL. La segunda las activa y
comprueba restricciones, triggers, concurrencia, adopción de tablas y reversión.
Utiliza el servidor y credenciales de `.env` para crear y eliminar bases
temporales `volumelab_test_<identifier>`; necesita permiso de creación de bases.
No escribe en `volumelab`. En Linux o macOS, usar `./env/bin/python`.

La exclusión corresponde a la suite antigua de valoraciones presente en `dev`,
que utiliza la base de trabajo. Su aislamiento está en la tarea de `workout`;
tras integrarla, ejecutar también la regresión completa sobre datos aislados.
Los 14 escenarios de `features/muscle_group.feature` se ejecutan en inglés.

## Equipo

| Miembro | Rol |
| --- | --- |
| **Jesús González** | Scrum Master |
| **William Hérnandez** | Product Owner |
| **Oscar Mauricio Mejía** | Developer |
| **Moisés García** | Developer |
| **Beatriz Iñiguez Cascales** | Developer |
