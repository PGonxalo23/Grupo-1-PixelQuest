# Pixel Quest

RPG de texto desarrollado en Python para la asignatura **Construcción de Software**. El proyecto demuestra programación orientada a objetos, arquitectura en capas y trabajo colaborativo mediante ramas y Pull Requests.

## Funcionalidades

- Creación de héroes Guerrero o Mago.
- Vida, ataque y defensa encapsulados.
- Inventario, armas, armaduras y equipamiento sin bonos acumulados por error.
- Mazmorra determinista de tres habitaciones.
- Combate por turnos contra un Goblin y un guardián final.
- Estados de victoria y derrota.
- Guardado y carga de partidas en JSON.
- Interfaz de consola con recuperación ante entradas inválidas.
- Pruebas unitarias y de integración con `unittest`.

## Requisitos

- Python 3.10 o superior.
- Git, únicamente para colaborar en el repositorio.
- No se requieren paquetes externos.

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

El proyecto utiliza exclusivamente la biblioteca estándar de Python, por lo que no requiere `pip install`.

## Ejecutar el juego

Abre una terminal en la raíz del repositorio:

```powershell
python -m src.main
```

No ejecutes `python src/main.py`; el comando como módulo garantiza que las importaciones de `src` funcionen correctamente.

## Menús

El menú principal permite:

- `1`: iniciar una nueva partida.
- `2`: cargar una partida guardada.
- `3`: continuar la partida en memoria.
- `0`: salir.

Durante la partida se puede consultar el estado, recoger y equipar objetos, atacar, avanzar y guardar.

El guardado local se crea en `data/savegame.json`. Este archivo está excluido de Git.

## Ejecutar pruebas

Suite completa:

```powershell
python -B -m unittest discover -s tests -v
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

## Arquitectura

El código sigue una arquitectura en tres capas:

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Dominio | `src/domain/` | Entidades, validaciones y reglas puras del RPG. |
| Servicios | `src/services/` | Casos de uso, flujo de partida y persistencia JSON. |
| Interfaz | `src/ui/` | Menús, entradas y presentación de resultados. |

`src/main.py` únicamente construye las dependencias y arranca la aplicación. Los diagramas Mermaid están en [`architecture.md`](architecture.md).

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
|       `-- cli_interface.py
|-- tests/
|   |-- test_domain.py
|   |-- test_models.py
|   |-- test_data_manager.py
|   |-- test_services.py
|   `-- test_integration.py
|-- .gitignore
|-- architecture.md
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

## Limitaciones del MVP

- Interfaz únicamente de texto.
- Una mazmorra de tres habitaciones.
- Dos clases de héroe.
- Sin multijugador, tienda, economía ni conexión a internet.
- Un único archivo local de guardado.
