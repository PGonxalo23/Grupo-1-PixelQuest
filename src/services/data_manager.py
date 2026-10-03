import json
from pathlib import Path


class PersistenceError(Exception):
    pass


class SaveNotFoundError(PersistenceError):
    pass


class InvalidSaveError(PersistenceError):
    pass


class DataManager:
    def __init__(self, path="data/savegame.json"):
        self._path = Path(path)

    def exists(self):
        try:
            return self._path.is_file()
        except OSError as exc:
            raise PersistenceError(
                "No se pudo consultar la partida guardada."
            ) from exc

    def save(self, state):
        if not isinstance(state, dict):
            raise InvalidSaveError("El estado debe ser un diccionario.")

        temporary_path = self._path.with_name(f"{self._path.name}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(
                    state,
                    file,
                    ensure_ascii=False,
                    indent=2
                )
            temporary_path.replace(self._path)
        except (OSError, TypeError, UnicodeEncodeError) as exc:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise PersistenceError(
                "No se pudo guardar la partida."
            ) from exc

    def load(self):
        if not self.exists():
            raise SaveNotFoundError(
                "No existe una partida guardada."
            )

        try:
            with self._path.open("r", encoding="utf-8") as file:
                data = json.load(file)

        except json.JSONDecodeError as exc:
            raise InvalidSaveError(
                "El archivo de guardado contiene JSON inválido."
            ) from exc

        except UnicodeDecodeError as exc:
            raise InvalidSaveError(
                "El archivo de guardado no utiliza codificación UTF-8 válida."
            ) from exc

        except OSError as exc:
            raise PersistenceError(
                "No se pudo leer la partida guardada."
            ) from exc

        if not isinstance(data, dict):
            raise InvalidSaveError(
                "El archivo de guardado debe contener un objeto JSON."
            )

        try:
            json.dumps(data, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidSaveError(
                "El archivo contiene texto Unicode no válido."
            ) from exc

        return data
