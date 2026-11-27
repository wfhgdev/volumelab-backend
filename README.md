# VolumeLab — Backend API

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-6BA81E)](https://alembic.sqlalchemy.org/)
[![Modelo de Datos](https://img.shields.io/badge/Esquema_BD-v4_(20--11--2026)-16a34a)](#modelo-de-datos)
[![RGPD](https://img.shields.io/badge/RGPD-Art._17_Derecho_de_Supresi%C3%B3n-2563eb)](#auditor%C3%ADa-autom%C3%A1tica-y-cumplimiento-rgpd)
[![Tests](https://github.com/wfhgdev/volumelab-backend/actions/workflows/tests.yml/badge.svg)](https://github.com/wfhgdev/volumelab-backend/actions/workflows/tests.yml)

API REST y capa de negocio del proyecto **VolumeLab** (Proyecto Deloitte), construida con **Python**, **FastAPI**, **PostgreSQL** y **Alembic**: plataforma de registro, planificación y análisis cuantitativo de entrenamiento de fuerza e hipertrofia.

Este repositorio centraliza la autenticación y autorización por roles, la gestión del catálogo de ejercicios y grupos musculares, la planificación por mesociclos y semanas, el registro granular de series (`1 fila = 1 serie`), el motor de cálculo automático de métricas de entrenamiento, las valoraciones comunitarias, la exportación de datos (CSV/Excel), la auditoría y el cumplimiento del RGPD.

---

## Tabla de contenidos

1. [Resumen del dominio](#resumen-del-dominio)
2. [Stack tecnológico](#stack-tecnol%C3%B3gico)
3. [Seguridad, autenticación y autorización](#seguridad-autenticaci%C3%B3n-y-autorizaci%C3%B3n)
4. [Roles y matriz detallada de permisos](#roles-y-matriz-detallada-de-permisos)
5. [Requisitos funcionales (RF-01 a RF-17)](#requisitos-funcionales-rf-01-a-rf-17)
6. [Reglas de negocio (RN-01 a RN-19)](#reglas-de-negocio-rn-01-a-rn-19)
7. [Motor de cálculo y responsabilidades del backend](#motor-de-c%C3%A1lculo-y-responsabilidades-del-backend)
8. [Modelo de datos](#modelo-de-datos)
   - [Diagrama Entidad-Relación](#diagrama-entidad-relaci%C3%B3n)
   - [Tipos enumerados (ENUM)](#tipos-enumerados-enum)
   - [Tablas principales](#tablas-principales)
   - [Vistas SQL](#vistas-sql)
   - [Triggers de integridad y negocio](#triggers-de-integridad-y-negocio)
9. [Auditoría automática y cumplimiento RGPD](#auditor%C3%ADa-autom%C3%A1tica-y-cumplimiento-rgpd)
10. [Estructura del repositorio](#estructura-del-repositorio)
11. [Manejo global de errores HTTP](#manejo-global-de-errores-http)
12. [Catálogo de entidades y endpoints API (CRUD)](#cat%C3%A1logo-de-entidades-y-endpoints-api-crud)
13. [Instalación, migraciones, seeders y ejecución local](#instalaci%C3%B3n-migraciones-seeders-y-ejecuci%C3%B3n-local)
14. [Equipo](#equipo)

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
| **Seguridad / Criptografía** | PyJWT + `pwdlib[argon2]` | Tokens de acceso JWT Bearer (HS256) y hasheo robusto de contraseñas con Argon2id |
| **Validación / Serialización** | Pydantic v2 | Validación de esquemas DTO de entrada/salida y configuración tipada (`pydantic-settings`) |
| **Base de datos** | PostgreSQL 14+ | Persistencia relacional (`UTF8`, `LC_CTYPE = 'es-ES'`), `ENUM`, vistas y triggers PL/pgSQL |
| **ORM / Driver** | SQLAlchemy 2.x + `psycopg` | Mapeo relacional síncrono, consultas analíticas y gestión transaccional estricta |
| **Migraciones** | Alembic | Versionado reproducible del esquema DDL, tipos `ENUM`, vistas y triggers |
| **Exportación** | CSV (`csv`) / Excel (`openpyxl` o `pandas`) | Exportación de registros y analíticas con trazabilidad en `audit` (**RF-15**) |
| **Testing** | `pytest` + `pytest-bdd` + `httpx` [![Tests](https://github.com/wfhgdev/volumelab-backend/actions/workflows/tests.yml/badge.svg)](https://github.com/wfhgdev/volumelab-backend/actions/workflows/tests.yml) | Pruebas unitarias, de integración, de seguridad/autorización y escenarios BDD (Gherkin) |

---

## Seguridad, autenticación y autorización

El backend implementa un modelo de seguridad por capas conforme a las especificaciones de **RF-01**, **RF-16** y **RN-17**:

### 1. Autenticación JWT (Bearer Token)
- **Estándar:** Tokens firmados mediante **HMAC-SHA256 (HS256)** con librería `PyJWT`, transmitidos en la cabecera `Authorization: Bearer <token>`.
- **Sin estado en cliente:** Sin cookies ni refresh tokens; tiempo de expiración configurable vía `ACCESS_TOKEN_EXPIRE_MINUTES` (por defecto 60 minutos).
- **Estructura de Claims del JWT:**
  - `sub`: Identificador único del usuario (cadena numérica, ej. `"42"`).
  - `role`: Rol del usuario en el momento de emisión (`ADMIN` o `CLIENTE`, meramente informativo).
  - `iat`: Timestamp Unix de emisión.
  - `exp`: Timestamp Unix de caducidad.
- **Validación en tiempo real:** Aunque el token contenga el claim `role`, el sistema **siempre consulta en base de datos el estado y rol real** del usuario en cada petición entrante (`get_current_user`). Esto garantiza que cambios de rol, desactivaciones o bloqueos de cuenta surtan efecto de forma inmediata sin esperar a que el token expire.

### 2. Criptografía y contraseñas
- **Hasheo seguro:** Implementado con **`pwdlib[argon2]`** utilizando `PasswordHash.recommended()`.
- **Compatibilidad de esquema:** Los hashes generados se alojan en la columna existente `app_user.password_hash` (`VARCHAR(255)`), sin requerir modificaciones DDL en la base de datos.
- **Políticas de complejidad:** Longitud obligatoria de 8 a 128 caracteres, preservando espacios interiores sin aplicar `strip` destructivo.
- **Sanitización de respuestas:** Ningún endpoint ni esquema de respuesta expone jamás el campo `password` ni `password_hash`. Además, SQLAlchemy mantiene `echo=False` para prevenir fugas de contraseñas, hashes o tokens en logs de consola.

### 3. Endpoints de autenticación pública (`/auth`)
- **`POST /auth/register`:** Registro de autoservicio para nuevos clientes.
  - Crea **siempre** un usuario con rol `CLIENTE` y estado `ACTIVO`.
  - Esquema estricto (`extra="forbid"`): si el cliente intenta enviar campos privilegiados como `role`, `status` o `password_hash`, la petición es rechazada inmediatamente con `422 Unprocessable Entity`.
- **`POST /auth/login`:** Generación de token JWT.
  - Mitigación contra enumeración de usuarios: responde exactamente el mismo código `401 Unauthorized` y el mismo mensaje en español tanto si el email no existe como si la contraseña es incorrecta.
  - Si el usuario existe pero su estado es `BLOQUEADO`, responde `403 Forbidden` informando "Usuario bloqueado".
- **`GET /auth/me`:** Devuelve el perfil del usuario autenticado actual (`ADMIN` o `CLIENTE`).

### 4. Códigos de respuesta de seguridad y control de acceso
- **`401 Unauthorized`:** Falta la cabecera `Authorization`, el token es inválido, ha expirado, o el usuario emisor ya no existe o no está `ACTIVO`.
- **`403 Forbidden`:** Usuario autenticado que no posee los privilegios requeridos por su rol (ej. un `CLIENTE` intentando acceder a rutas de administración o crear recursos a nombre de otro usuario).
- **`404 Not Found`:** Cuando un `CLIENTE` intenta acceder por ID a un recurso privado perteneciente a otro usuario (ocultamiento intencionado de existencia).

---

## Roles y matriz detallada de permisos

El sistema diferencia entre dos roles de usuario: **`ADMIN`** y **`CLIENTE`**:

| Recurso / Endpoint | `ADMIN` | `CLIENTE` |
| --- | --- | --- |
| `/auth/register`, `/auth/login` | Público | Público |
| `/auth/me` | Consulta su perfil | Consulta su perfil |
| `/app-users/` | CRUD completo; puede fijar `role` y `status` | `POST`: `403`. `GET` lista: `403`. `GET/PUT/DELETE /{id}`: solo su propia cuenta (otro ID → `404`). Intento de modificar `role` o `status` → `403`. |
| `/muscle-groups/` | CRUD completo (**exclusivo**) | Solo lectura (`GET` listado y detalle). `POST`, `PUT`, `DELETE` → `403`. |
| `/audits/` | **Solo lectura:** `GET /` y `GET /{id}` | `403 Forbidden` en todas las operaciones. |
| `/workouts/` | Acceso y gestión total | Crear (`created_by` forzado a su ID; máx. 20 públicos). `GET`: propios + públicos. `PUT`/`DELETE`: solo ejercicios propios. |
| `/muscle-workouts/` | Acceso total | Crear/borrar asociaciones únicamente sobre ejercicios propios. `GET`: ejercicios visibles. |
| `/weight-history/` | Consulta y gestión global | Solo sus propios registros de peso. |
| `/mesocycles/` | Consulta y supervisión global | Solo sus propios mesociclos. |
| `/training-weeks/` | Consulta y supervisión global | Solo semanas de mesociclos propios (`training_week` → `mesocycle.user_id`). |
| `/workout-sessions/` | Acceso y gestión total | Crear con su `user_id` (máx. 20 públicas). `GET`: propias + públicas. `PUT`/`DELETE`: solo sesiones propias. |
| `/workout-sets/` | Supervisión total | Crear/editar/borrar solo en sesiones propias abiertas (`ABIERTO`). `GET`: en sesiones que tiene permiso de ver (`workout_set` → `workout_session.user_id`). |
| `/session-rates/`, `/workout-rates/` | Acceso y gestión total | Crear, upsert, editar y borrar **únicamente su propia valoración** (1 voto actualizable por recurso). Consultar puntuaciones agregadas y notas medias. |

### Reglas de visibilidad y propiedad
1. **Recursos privados vs. públicos:** Un recurso privado (`public = FALSE`) solo es accesible por su dueño o por un `ADMIN`. Un recurso público (`public = TRUE`) puede ser leído por cualquier usuario autenticado, pero **solo su creador original o un `ADMIN` pueden modificarlo o eliminarlo**.
2. **Resolución automática de propietario (`resolve_owner_id`):** En todos los esquemas `*Create`, los campos `user_id` y `created_by` son opcionales:
   - Para un `CLIENTE`: Si se omite, el sistema asigna automáticamente el ID del usuario autenticado. Si el cliente envía un ID distinto al suyo, se rechaza con `403 Forbidden`.
   - Para un `ADMIN`: Permite especificar un ID de usuario destino para crear recursos a nombre de otros usuarios; si se omite, se asigna a sí mismo.
3. **Filtros en listados:** En consultas de listado (`GET /`), para un `CLIENTE` el filtro de propietario se fuerza automáticamente al suyo (más recursos públicos donde corresponda). Para un `ADMIN`, el filtro de usuario es opcional para permitir auditoría global.

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

## Auditoría automática y cumplimiento RGPD

### 1. Sistema de auditoría automática (`audit` — RF-15, RF-16)
- **Registro append-only generado por el sistema:** Ningún usuario (incluido `ADMIN`) puede insertar, modificar o borrar registros de auditoría a través de la API. Los endpoints `POST /audits/`, `PUT /audits/{id}` y `DELETE /audits/{id}` están expresamente inhabilitados (responden `405 Method Not Allowed`).
- **Control de acceso a auditoría:** **Solo los usuarios con rol `ADMIN`** pueden consultar registros de auditoría (`GET /audits/` y `GET /audits/{id}`). Un usuario `CLIENTE` recibe `403 Forbidden`.
- **Qué se audita:**
  - Cada operación exitosa de creación (`INSERT`), modificación (`UPDATE`) o eliminación (`DELETE`) sobre cualquier entidad del sistema, efectuada por cualquier usuario autenticado (`ADMIN` o `CLIENTE`).
  - El autorregistro de nuevos usuarios (`POST /auth/register`) se audita automáticamente como `INSERT` en `app_user` asociado al ID del usuario recién creado.
  - Endpoints de tipo upsert registran `INSERT` o `UPDATE` según la acción real ejecutada.
  - Exportaciones de datos a CSV/Excel registran `EXPORT` (**RF-15**).
- **Qué NO se audita:**
  - Peticiones de lectura (`GET`).
  - Peticiones fallidas (errores `401`, `403`, `404`, `409`, `422`, `500`).
  - Intentos de login o logout (el enum `audit_action` no almacena eventos de sesión).
  - Operaciones sobre la propia tabla `audit` (evitando recursión infinita).
  - La ejecución de seeders de inicialización del sistema.
- **Campos registrados y privacidad:**
  - `user_id`: ID del usuario que realizó la acción.
  - `entity`: Nombre de la tabla en snake_case (`workout`, `workout_session`, `workout_set`, etc.).
  - `record_id`: Identificador en formato string (clave compuesta separada por `:` en `muscle_workout`, ej. `"3:1"`).
  - `action`: `INSERT`, `UPDATE`, `DELETE` o `EXPORT`.
  - `endpoint`: Método y ruta sin query params (ej. `"POST /workout-sessions/"`), truncado a 255 caracteres.
  - **Privacidad estricta:** La auditoría **nunca** almacena contraseñas, hashes, tokens de acceso ni cuerpos de petición.
- **Consistencia transaccional:** La inserción de la traza de auditoría ocurre **dentro de la misma transacción de base de datos** que la acción auditada (ambas se confirman o ambas se revierten automáticamente).

### 2. Cumplimiento del derecho de supresión (RGPD, art. 17 — RN-19)
Al ejecutar la eliminación de un usuario (`DELETE /app-users/{id}`):
- **Eliminación en cascada (`ON DELETE CASCADE`):** Elimina irreversiblemente `weight_history`, `mesocycle` → `training_week`, `workout_session` → `workout_set`, `session_rate`, `workout_rate` y todas sus trazas en `audit`.
- **Anonimización del catálogo compartido (`ON DELETE SET NULL`):** Los ejercicios (`workout`) y grupos musculares (`muscle_group`) creados por el usuario se conservan con `created_by = NULL` para no romper el historial de entrenamientos de otros usuarios que tengan series vinculadas (`ON DELETE RESTRICT`).

---

## Estructura del repositorio

```text
volumelab-backend/
├── app/
│   ├── api/                    # Routers FastAPI para cada una de las 12 entidades
│   ├── controllers/            # Controladores con lógica de negocio y operaciones de BD
│   ├── core/                   # Configuración (.env), conexión BD y manejadores globales de error
│   ├── models/                 # Modelos ORM SQLAlchemy 2.0 (12 entidades)
│   ├── schemas/                # Esquemas Pydantic v2 (DTOs request/response con validaciones)
│   └── main.py                 # Instancia de FastAPI, registro de routers y handlers de error
├── db/
│   └── volumelab_20-11-2026_v4.sql   # Script SQL canónico de referencia del esquema v4
├── features/                   # Escenarios de especificación BDD en Gherkin (.feature)
├── migrations/                 # Migraciones de Alembic (versions/, env.py, script.py.mako)
├── tests/                      # Suite de pruebas automatizadas (unitarias, integración y BDD)
│   └── features/               # Escenarios BDD adicionales
├── alembic.ini                 # Configuración de migraciones Alembic
├── requirements.txt            # Dependencias del proyecto
├── .env.example                # Variables de entorno de referencia
└── README.md
```

---

## Manejo global de errores HTTP

El backend implementa una arquitectura centralizada y DRY para la traducción de excepciones de base de datos a códigos de estado y respuestas HTTP estructuradas mediante interceptores globales en [app/core/exception_handlers.py](file:///c:/Github/VolumeLab_backend/app/core/exception_handlers.py):

- **`IntegrityError` (Violaciones de Integridad Referencial y Restricciones):**
  - **`23505` (Violación de unicidad / `UniqueViolation`):** Retorna `409 Conflict` (ej. nombres duplicados en `workout` y `muscle_group`, duplicados en `muscle_workout` o email en `app_user`).
  - **`23503` / `23001` (Violación de clave foránea / `ForeignKeyViolation`):** Retorna `409 Conflict` ante eliminaciones bloqueadas por `ON DELETE RESTRICT` (ej. borrar un ejercicio con series o un grupo muscular asociado).
  - **`23514` (Violación de restricción `CHECK`):** Retorna `422 Unprocessable Entity` ante valores fuera de rango de dominio o combinaciones incompatibles.
  - **`23502` (Violación de `NOT NULL`):** Retorna `422 Unprocessable Entity` cuando se omiten campos obligatorios.

- **`DBAPIError` (Triggers PL/pgSQL y Tipos de Datos):**
  - **`22P02` (Tipo de dato o enumerado inválido):** Retorna `422 Unprocessable Entity`.
  - **`P0001` (Excepciones emitidas por triggers PL/pgSQL):**
    - `trg_muscle_group_admin_only`: Retorna `403 Forbidden` si un usuario no administrador intenta crear o reasignar un grupo muscular (**RN-17**).
    - `trg_workout_client_limit` y `trg_session_client_limit`: Retorna `409 Conflict` si un cliente intenta superar la cuota máxima de 20 recursos públicos (**RN-17**).
    - `trg_workout_set_session_open`: Retorna `409 Conflict` si se intenta insertar, modificar o borrar series en una sesión cerrada (**RN-07**).
    - `trg_workout_set_check_type`: Retorna `422 Unprocessable Entity` si no se cumplen las reglas de duración en isométricos o repeticiones en dinámicos (**RN-04**, **RN-10**, **RN-12**).

- **`HTTPException` en Controladores:**
  - Reservadas exclusivamente para validaciones lógicas previas de negocio (ej. comprobaciones de estado antes de operar) y recursos no encontrados (`404 Not Found`).

---

## Catálogo de entidades y endpoints API (CRUD)

Todas las entidades del sistema cuentan con su ciclo de vida CRUD estandarizado y uniforme a través de FastAPI, SQLAlchemy 2.0 y Pydantic v2:

| Entidad | Prefijo de Ruta | Métodos REST Soportados | Descripción y Reglas Clave |
| --- | --- | --- | --- |
| **`app_user`** | `/app-users/` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Cuentas, roles (`ADMIN`, `CLIENTE`) y estados (`ACTIVO`, `BLOQUEADO`). El borrado físico ejecuta el derecho de supresión RGPD (Art. 17). |
| **`weight_history`** | `/weight-history/` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Histórico cronológico de peso corporal del usuario. Fija la instantánea en cada sesión de entrenamiento. |
| **`mesocycle`** | `/mesocycles/` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Planificación de bloques macro con control de estados (`PLANIFICADO`, `ACTIVO`, `FINALIZADO`). |
| **`training_week`** | `/training-weeks/` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Semanas numeradas (`week_order`) contenidas en un mesociclo. Al eliminarse desvincula sesiones sin borrarlas (`SET NULL`). |
| **`workout_session`** | `/workout-sessions/` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Sesiones de entrenamiento. Control de apertura/cierre (`ABIERTO`, `CERRADO`), snapshot de peso y máx. 20 públicas para clientes. |
| **`workout`** | `/workouts/` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Catálogo de ejercicios (dinámicos e isométricos). Desactivación lógica (`state = false`) para proteger series históricas. |
| **`muscle_group`** | `/muscle-groups/` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | Catálogo maestro de grupos musculares. Creación exclusiva por `ADMIN`. Borrado físico protegido frente a asociaciones existentes. |
| **`muscle_workout`** | `/muscle-workouts/` | `POST`, `GET`, `GET /{workout_id}/{muscle_group_id}`, `PUT`, `DELETE` | Asociación N:M con clave compuesta. Ponderación automática (`PRIMARIO`: 100, `SECUNDARIO`: 50, `TERCIARIO`: 10). Bloquea cambios si el ejercicio ya tiene series. |
| **`workout_set`** | `/workout-sets/` | `POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` | **1 fila = 1 serie.** Motor de cálculo de peso efectivo, 1RM, %1RM y volumen. Bloqueado si la sesión está en estado `CERRADO`. |
| **`workout_rate`** | `/workout-rates/` | `POST`, `POST /upsert`, `GET`, `GET /{id}`, `GET /score`, `GET /user`, `PUT`, `DELETE` | Puntuaciones de 1 a 5 en ejercicios públicos y activos. Nota media y recuento dinámico expuestos vía vista SQL. |
| **`session_rate`** | `/session-rates/` | `POST`, `POST /upsert`, `GET`, `GET /{id}`, `GET /score`, `GET /user`, `PUT`, `DELETE` | Puntuaciones de 1 a 5 en sesiones públicas. Nota media y recuento dinámico expuestos vía vista SQL. |
| **`audit`** | `/audits/` | `GET`, `GET /{id}` | Registro de trazabilidad append-only. Solo lectura para `ADMIN`. Endpoints de escritura (`POST`, `PUT`, `DELETE`) inhabilitados (`405 Method Not Allowed`). |

---

## Instalación, migraciones, seeders y ejecución local

### 1. Requisitos previos

- **Python 3.11+**
- **PostgreSQL 14+** con codificación `UTF8` y configuración regional española (`LC_CTYPE = 'es-ES'`).

### 2. Clonar el repositorio y configurar el entorno virtual

```bash
git clone <URL_DEL_REPOSITORIO_BACKEND>
cd volumelab-backend

# Crear el entorno virtual
python -m venv env

# Activar en Windows (PowerShell)
.\env\Scripts\Activate.ps1

# Activar en Linux / macOS
source env/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración de variables de entorno

Crear un archivo `.env` en la raíz del proyecto a partir de `.env.example`:

```env
# Conexión a la base de datos PostgreSQL
DATABASE_URL=postgresql+psycopg://postgres:changeme@localhost:5432/volumelab

# Seguridad / JWT
SECRET_KEY=clave_secreta_para_desarrollo_local
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Administrador inicial (opcional para el seeder)
ADMIN_EMAIL=admin@volumelab.com
ADMIN_PASSWORD=Admin1234!

# Configuración de la aplicación
APP_NAME=VolumeLab Backend
APP_VERSION=1.0.0
APP_DESCRIPTION=API REST para VolumeLab
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 4. Migraciones de la base de datos (Alembic)

Para aplicar todas las migraciones acumuladas del esquema hasta las últimas revisiones (*heads*):

```bash
alembic upgrade heads
```

> **Nota:** Se utiliza `heads` (en plural) debido a que existen ramas paralelas de migración y puntos de unión (*mergepoints*) para tablas independientes como `workout_set` y `audit`.

Comandos habituales de soporte:
```bash
# Comprobar la revisión actual aplicada
alembic current

# Generar una nueva migración por cambios en modelos
alembic revision --autogenerate -m "descripcion_del_cambio"

# Historial de migraciones
alembic history
```

### 5. Creación del Administrador inicial y datos de prueba (Seeders)

Para inicializar la base de datos con el usuario administrador inicial (hasheando su contraseña de forma segura con Argon2id):

```bash
python -m seeders.run --entity admin
```

*(En Windows PowerShell: `.\env\Scripts\python -m seeders.run --entity admin`)*

- **Credenciales por defecto:**
  - **Email:** `admin@volumelab.com`
  - **Contraseña:** `Admin1234!`
  - **Rol:** `ADMIN` | **Estado:** `ACTIVO`
- **Idempotencia:** El script puede ejecutarse múltiples veces de forma segura. Si el email ya existe (búsqueda insensible a mayúsculas/minúsculas), no duplica ni modifica el usuario.
- **Otros seeders disponibles:**
  ```bash
  # Poblar valoraciones de prueba
  python -m seeders.run --entity session_rate --count 50
  python -m seeders.run --entity workout_rate --count 50

  # Poblar todo el conjunto
  python -m seeders.run --entity all
  ```

### 6. Iniciar el servidor de desarrollo

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La documentación interactiva y el catálogo OpenAPI estarán accesibles en:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### 7. Ejecución de pruebas

El proyecto cuenta con una amplia suite de pruebas automatizadas (unitarias, integración, control de acceso por roles y escenarios BDD en Gherkin):

```bash
# Ejecutar la suite completa de pruebas unitarias, integración y BDD
pytest -v -m "not postgres"

# Ejecutar todas las pruebas (incluyendo las que requieren base de datos PostgreSQL real)
pytest -v

# Ejecutar pruebas PostgreSQL sobre bases de datos desechables aisladas
pytest -v --run-postgres
```

---

## Equipo

| Miembro | Rol |
| --- | --- |
| **Jesús González** | Scrum Master |
| **William Hérnandez** | Product Owner |
| **Oscar Mauricio Mejía** | Developer |
| **Moisés García** | Developer |
| **Beatriz Iñiguez Cascales** | Developer |
