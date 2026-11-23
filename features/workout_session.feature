Feature: Gestión de sesiones de entrenamiento
  Como usuario de VolumeLab
  Quiero registrar sesiones de entrenamiento
  Para mantener el historial de mi actividad

  Scenario: Crear una sesión con una semana del mismo usuario
    Given existe un usuario CLIENTE con identificador 1
    And existe una semana de entrenamiento del usuario 1
    When creo una sesión para el usuario 1 con la semana del usuario 1
    Then la respuesta tiene el código de estado 201
    And la sesión pertenece al usuario 1

  Scenario: Rechazar una semana que pertenece a otro usuario
    Given existe un usuario CLIENTE con identificador 1
    And existe un usuario CLIENTE con identificador 2
    And existe una semana de entrenamiento del usuario 2
    When creo una sesión para el usuario 1 con la semana del usuario 2
    Then la respuesta tiene el código de estado 422

  Scenario: Rechazar la vigésima primera sesión pública de un CLIENTE
    Given existe un usuario CLIENTE con identificador 1
    And el usuario 1 tiene 20 sesiones públicas
    When creo una sesión pública para el usuario 1
    Then la respuesta tiene el código de estado 422

  Scenario: Rechazar un campo obligatorio nulo al actualizar una sesión
    Given existe un usuario CLIENTE con identificador 1
    And existe una sesión del usuario 1
    When actualizo el usuario de esa sesión a nulo
    Then la respuesta tiene el código de estado 422
