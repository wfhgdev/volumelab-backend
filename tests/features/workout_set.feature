Feature: Gestión de series de entrenamiento (workout_set)
  Como usuario de VolumeLab
  Quiero registrar y validar series de una sesión
  Para calcular volumen, intensidad y respetar las reglas de negocio

  Scenario: Crear una serie dinámica calcula volumen y 1RM
    Given una sesión abierta con ejercicios base
    When envío una serie dinámica con peso 50, 10 repeticiones y RIR 0
    Then la respuesta debe tener el código de estado 201
    And el volumen calculado debe ser 500
    And el 1RM estimado debe ser 66.67

  Scenario: Crear una serie isométrica calcula el volumen por duración
    Given una sesión abierta con ejercicios base
    When envío una serie isométrica con peso 20 y 40 segundos
    Then la respuesta debe tener el código de estado 201
    And el volumen calculado debe ser 800
    And el 1RM estimado debe ser nulo

  Scenario: Rechazar una serie de un ejercicio desactivado
    Given una sesión abierta con ejercicios base
    And el ejercicio 1 está desactivado
    When envío una serie dinámica con peso 50, 10 repeticiones y RIR 0
    Then la respuesta debe tener el código de estado 422

  Scenario: Rechazar lastre negativo no permitido
    Given una sesión abierta con ejercicios base
    When envío una serie dinámica con peso externo -25, 10 repeticiones y RIR 0
    Then la respuesta debe tener el código de estado 422

  Scenario: Rechazar series en una sesión cerrada
    Given una sesión abierta con ejercicios base
    And la sesión está cerrada
    When envío una serie dinámica con peso 50, 10 repeticiones y RIR 0
    Then la respuesta debe tener el código de estado 409

  Scenario: Rechazar dos ejercicios distintos en la misma posición
    Given una sesión abierta con ejercicios base
    And ya existe una serie del ejercicio 1 en la posición 1
    When envío una serie del ejercicio 2 en la posición 1 y número de serie 2
    Then la respuesta debe tener el código de estado 409
