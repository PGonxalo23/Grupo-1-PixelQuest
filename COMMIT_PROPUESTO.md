# Commit propuesto — pendiente de validación humana

Este documento es una propuesta de mensaje. No se ha creado el commit ni se ha publicado la rama.

## Mensaje

```text
feat: integrar RPG visual 2D con personalización del héroe

- Agregar exploración de mazmorra y pixel art original con Pygame.
- Conectar combate visual por turnos, inventario y equipamiento a GameService.
- Incorporar selección y persistencia del color del héroe.
- Guardar posición y conservar compatibilidad con partidas de consola.
- Mantener ejecución CLI mediante --cli.
- Actualizar documentación y agregar pruebas de integración gráfica.

Validación automatizada: 72 pruebas aprobadas.
Validación humana: [completar después de probar en VS Code].
```

## Datos para el futuro Pull Request

**Célula de desarrollo:** Interfaz e Integración, con cambios coordinados de Dominio y Servicios.

**Responsable:** [nombre e integrante].

**Rama local:** `feature/2d-rpg`.

**Base de integración actual:** `chore/project-scaffold`. Confirmar con el GitMaster la base del PR; la rama predeterminada del repositorio no es `main`.

### Distribución de cambios para revisión por célula

- Dominio: `src/domain/models.py`, `src/domain/validators.py`.
- Servicios: `src/services/app_service.py`.
- Interfaz/Integración: `src/ui/`, `src/main.py`.
- Integrador: `requirements.txt`, `JUGAR.bat`, documentación y pruebas.

La `.venv`, las partidas y `.vscode` son archivos locales excluidos de Git.

## Prompts exactos utilizados

Solicitud de ampliación:

```text
necesito que veas el repositorio y lo actualices, este tiene implementado nuevas unciones pero el problema es que sigue siendo de consola, quiero que sea visual, en 2d, que siga cumpliendo con lo que pide el documento guía como el cabio de color de personajes y poder matar enemigos como un rpg, pero no lo vas a subir al repositorio todavía porque se tiene que hacer pruebas, asi que antes me daras el formato del commit
```

Aclaraciones del usuario:

```text
ESTÁ AQUI C:\Users\marce\Desktop\construc software
Exploración y turnos (Recomendado)
```

Autorización para implementar:

```text
IMPLEMENTA, RECUERDA NO SUBIRLO AL REPOSITORIO
```

## Evidencia

Consultar `PRUEBAS_LOCALES.md` para los resultados automatizados y la lista de pruebas manuales. Completar esa validación y el nombre del responsable antes de preparar cualquier commit o PR.
