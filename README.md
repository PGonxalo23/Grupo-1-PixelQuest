# Pixel Quest

RPG **visual 2D** desarrollado en Python y Pygame para la asignatura **Construcción de Software**. El proyecto demuestra programación orientada a objetos, arquitectura en capas y trabajo colaborativo mediante ramas y Pull Requests. Conserva una interfaz CLI opcional para la demostración de consola.

## Funcionalidades

- Creación de héroes Guerrero o Mago.
- Elección de seis colores con vista previa y personalización durante la partida.
- Exploración 2D con movimiento, colisiones, objetos y puertas bloqueadas por enemigos.
- Pixel art original generado por código, sin descargas de imágenes ni recursos externos.
- Vida, ataque y defensa encapsulados.
- Inventario, armas, armaduras y equipamiento sin bonos acumulados por error.
- Mazmorra determinista de tres habitaciones.
- Combate por turnos contra un Goblin y un guardián final.
- Animaciones de ataque, proyectiles del Mago, daño flotante y barras de vida.
- Estados de victoria y derrota.
- Guardado y carga de partidas en JSON.
- Persistencia del color y posición; compatibilidad con partidas antiguas de consola.
- Ventana redimensionable, inventario gráfico, pausa y pantallas de victoria/derrota.
- Interfaz de consola con recuperación ante entradas inválidas.
- Pruebas unitarias y de integración con `unittest`.

## Requisitos

- Python 3.10 o superior.
- Git, únicamente para colaborar en el repositorio.
- Pygame 2.6.1 o superior, instalado mediante `requirements.txt`.

Comprueba tu instalación:

```powershell
python --version
git --version
```

## Instalación

```powershell
git clone https://github.com/PGonxalo23/Grupo-1-PixelQuest.git
cd Grupo-1-PixelQuest
```

Desde la raíz del repositorio, prepara el entorno local en Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si el entorno `.venv` ya está preparado, no es necesario volver a crearlo.

## Ejecutar el juego

Abre una terminal en la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -B -m src.main
```

El juego abre una ventana gráfica. También puedes hacer doble clic en **`JUGAR.bat`**. El punto de entrada admite el botón **Run Python File** de VS Code y encuentra el directorio del proyecto aunque la terminal esté en otra carpeta.

### Visual Studio Code

1. Abre la carpeta `Grupo-1-PixelQuest` con **Archivo → Abrir carpeta**.
2. Instala las extensiones recomendadas de Python, Pylance y Python Debugger.
3. Selecciona `.venv\Scripts\python.exe` con **Python: Select Interpreter**.
4. En **Ejecutar y depurar**, selecciona **Pixel Quest · RPG 2D** y pulsa **F5**.
5. La configuración local incluye una tarea **Pixel Quest: pruebas** y descubrimiento de `unittest`.

Los archivos `.vscode/` son configuración local y están excluidos de Git, según la guía.

### Controles gráficos

| Control | Acción |
|---|---|
| WASD / flechas | Mover al héroe. |
| E | Recoger un objeto, atacar al enemigo cercano o atravesar la puerta. |
| Espacio | Atacar al enemigo cercano. |
| I | Abrir/cerrar inventario; clic o teclas 1/2 para equipar. |
| C | Cambiar el color con vista previa; aplicar o cancelar. |
| Esc | Pausar, continuar o cerrar una pantalla secundaria. |
| F5 | Guardar la partida explícitamente. |
| F9 | Cargar el último guardado explícitamente. |

El combate **es por turnos**: un ataque del héroe genera un contraataque si el enemigo sobrevive. Durante la animación no se puede ejecutar otro turno. Moverse, equiparse y personalizarse no consumen turnos de combate.

Ruta sugerida: recoge la espada en la primera sala con **E**, equípala con **I**, cruza la puerta derecha, derrota al Goblin, recoge y equipa la armadura y enfrenta al jefe final.

### Consola y comprobación de arranque

```powershell
.\.venv\Scripts\python.exe -B -m src.main --cli
.\.venv\Scripts\python.exe -B -m src.main --smoke-test
```

`--cli` también funciona con Python estándar sin Pygame. `--smoke-test` abre tres frames y termina sin crear una partida. Para usar un guardado alternativo: `--save-path "data/prueba.json"`.

## Menús de consola (`--cli`)

El menú principal permite:

- `1`: iniciar una nueva partida.
- `2`: cargar una partida guardada.
- `3`: continuar la partida en memoria.
- `0`: salir.

Durante la partida se puede consultar el estado, recoger y equipar objetos, atacar, avanzar y guardar.

Ambas interfaces usan `data/savegame.json`, relativo al proyecto. Este archivo está excluido de Git. Un guardado realizado en consola conserva el color, pero omite la posición gráfica; al volver al modo 2D el héroe aparece en la entrada de su sala. No hay guardado automático al salir.

## Ejecutar pruebas

Suite completa:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Pruebas por módulo:

```powershell
python -B -m unittest tests.test_domain -v
python -B -m unittest tests.test_models -v
python -B -m unittest tests.test_data_manager -v
python -B -m unittest tests.test_services -v
python -B -m unittest tests.test_integration -v
```

La opción `-B` evita generar archivos `.pyc` durante la validación.

Las pruebas gráficas usan SDL en modo `dummy` y recorren eventos reales de teclado y ratón, colisiones, ambas clases hasta la victoria, derrota, pausa, colores y persistencia. Si Pygame no está instalado se omiten explícitamente; ejecuta la suite con `.venv` para comprobar todo.

Resultado local de esta implementación: **72 pruebas aprobadas**. El arranque también se comprobó con el controlador real de ventanas de Windows. La evaluación manual del estudiante sigue pendiente en [`PRUEBAS_LOCALES.md`](PRUEBAS_LOCALES.md).

## Arquitectura

El código sigue una arquitectura en tres capas:

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Dominio | `src/domain/` | Entidades, validaciones y reglas puras del RPG. |
| Servicios | `src/services/` | Casos de uso, flujo de partida y persistencia JSON. |
| Interfaz | `src/ui/` | Menús, entradas y presentación de resultados. |

`src/main.py` únicamente construye las dependencias y arranca la aplicación. Los diagramas Mermaid están en [`architecture.md`](architecture.md).

La vista gráfica se reparte en `graphical_interface.py` (pantallas y eventos), `pixel_art.py` (gráficos), `world.py` (exploración) y `visual_persistence.py` (metadatos de posición). El dominio y el servicio de combate no importan Pygame.

## Estructura

```text
pixel-quest/
|-- .github/
|   `-- pull_request_template.md
|-- data/
|   `-- .gitkeep
|-- src/
|   |-- __init__.py
|   |-- main.py
|   |-- domain/
|   |   |-- __init__.py
|   |   |-- exceptions.py
|   |   |-- models.py
|   |   `-- validators.py
|   |-- services/
|   |   |-- __init__.py
|   |   |-- app_service.py
|   |   `-- data_manager.py
|   `-- ui/
|       |-- __init__.py
|       |-- cli_interface.py
|       |-- graphical_interface.py
|       |-- pixel_art.py
|       |-- world.py
|       `-- visual_persistence.py
|-- tests/
|   |-- test_domain.py
|   |-- test_models.py
|   |-- test_data_manager.py
|   |-- test_services.py
|   |-- test_integration.py
|   |-- test_visual_state.py
|   `-- test_graphical.py
|-- .gitignore
|-- architecture.md
|-- requirements.txt
|-- JUGAR.bat
|-- PRUEBAS_LOCALES.md
|-- COMMIT_PROPUESTO.md
`-- README.md
```

## Distribución del equipo

| Integrante | Rol | Archivos principales |
|---|---|---|
| Integrante 1 | Líder de Dominio Core | `models.py`, `test_models.py` |
| Integrante 2 | Reglas y Excepciones | `exceptions.py`, `validators.py`, `test_domain.py` |
| Integrante 3 | Servicios y Lógica | `app_service.py`, `test_services.py` |
| Integrante 4 | Persistencia JSON | `data_manager.py`, `test_data_manager.py` |
| Integrante 5 | GitMaster, UI e Integración | `cli_interface.py`, `main.py`, documentación y pruebas integradas |

Los nombres reales y usuarios de GitHub deben completarse antes de la entrega.

## Flujo Git

- Nadie desarrolla directamente en `main`.
- Cada tarea utiliza una rama independiente.
- Cada Pull Request incluye el prompt exacto de IA y la evidencia de pruebas.
- Otro integrante revisa el cambio.
- Solo el GitMaster realiza el merge autorizado.
- La rama `main` debe permanecer ejecutable.

Convenciones utilizadas:

```text
feature/domain-models
feature/domain-validations
feature/json-persistence
feature/service-gameplay
feature/cli-integration
```

## Uso auditado de IA

La IA se utiliza como copiloto. Cada integrante debe:

1. Registrar en el PR el prompt realmente utilizado.
2. Leer y comprender el código generado.
3. Ejecutar las pruebas de su módulo.
4. Corregir incompatibilidades antes de solicitar revisión.
5. No atribuirse código perteneciente a otra célula.

Los prompts de esta ampliación y el mensaje de commit propuesto están en [`COMMIT_PROPUESTO.md`](COMMIT_PROPUESTO.md). Los cambios de color requieren colaboración entre Dominio, Servicios e Interfaz: el documento identifica las carpetas correspondientes para su revisión por célula.

## Limitaciones del MVP

- Una mazmorra de tres habitaciones.
- Dos clases de héroe.
- Combate por turnos, sin combate en tiempo real.
- Sin multijugador, tienda, economía ni conexión a internet.
- Un único archivo local de guardado.
