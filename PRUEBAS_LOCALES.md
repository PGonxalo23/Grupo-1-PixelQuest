# Validación local de Pixel Quest 2D

## Entorno comprobado por el agente

- Windows, Python 3.12.10 y Pygame 2.6.1 dentro de `.venv`.
- Base actualizada a `e10d1ad` de `chore/project-scaffold`.
- Rama de trabajo local: `feature/2d-rpg`.
- No se creó ningún commit ni se publicó la rama.

## Evidencia automatizada

Comando:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Resultado:

```text
Ran 72 tests
OK
```

Cobertura de comportamiento:

- Reglas de dominio, inventario, combate y persistencia existentes.
- Partidas gráficas completas hasta victoria con Guerrero y Mago.
- Derrota por contraataque y recuperación después de pausar la animación.
- Eventos reales de teclado y ratón, incluidos clics tras redimensionar la ventana.
- Colisiones de paredes, columnas y enemigos; velocidad diagonal normalizada.
- Ataque bloqueado a distancia y prevención de turnos duplicados durante la animación.
- Selección y cambio de color sin modificar las estadísticas de combate.
- Guardado/carga de color, equipo, daño, posición y resultado final.
- Compatibilidad con guardados de consola sin color ni posición.
- Recuperación ante JSON/Unicode inválido y metadatos visuales inseguros.

También se comprobó el arranque de la ventana con `--smoke-test` usando el controlador real de Windows. Se revisaron capturas del menú, creación del héroe, sala inicial, combate e inventario. Las pruebas automatizadas de interfaz usan SDL `dummy`.

## Pruebas manuales pendientes del estudiante

Estos puntos no se consideran completados por ejecutar pruebas automatizadas:

- [ ] Abrir la carpeta del proyecto en VS Code y seleccionar `.venv`.
- [ ] Iniciar el RPG 2D con F5 y comprobar legibilidad y fluidez.
- [ ] Crear un Guerrero y un Mago con nombre y color personalizados.
- [ ] Caminar con WASD y flechas; comprobar que paredes y columnas bloquean el paso.
- [ ] Recoger la espada con E y equiparla con I.
- [ ] Derrotar al Goblin; recoger y equipar la armadura.
- [ ] Cambiar de color, cancelar una selección y aplicar otra.
- [ ] Guardar con F5, cerrar, abrir y cargar desde el menú.
- [ ] Comprobar color, posición, vida y equipamiento después de cargar.
- [ ] Derrotar al jefe final y comprobar la pantalla de victoria.
- [ ] Comprobar la pantalla de derrota y el botón de nueva aventura.
- [ ] Redimensionar la ventana y verificar que los botones siguen respondiendo.
- [ ] Ejecutar `--cli` y validar el flujo requerido para la demo de consola.
- [ ] Leer los cambios de cada capa y registrar la revisión humana antes del PR.

## Observaciones de la guía

La Guía de Laboratorio N.º 6 permite menú de consola o interfaz gráfica y exige capas POO, Mermaid, evidencia de pruebas y prompts exactos en los PR. Su rúbrica menciona consola; por eso se conserva `--cli`.

La selección de color es un requisito adicional solicitado por el usuario. El proyecto mantiene tres habitaciones, dos clases y el combate por turnos de la base original.
