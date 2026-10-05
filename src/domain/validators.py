from src.domain.exceptions import (
    InvalidNameError,
    InvalidStatError,
    InvalidItemError,
    ValidationError,
)

def validate_name(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidNameError("El nombre debe ser un texto.")
    cleaned_name = value.strip()
    if not cleaned_name:
        raise InvalidNameError("El nombre no puede estar vacío.")
    return cleaned_name

def validate_positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidStatError(f"El campo {field} debe ser un entero estrictamente positivo (> 0).")
    return value

def validate_non_negative_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidStatError(f"El campo {field} debe ser un entero no negativo (>= 0).")
    return value

def validate_item_type(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidItemError("El tipo de objeto debe ser un texto.")
    normalized = value.strip().lower()
    if normalized not in ("weapon", "armor"):
        raise InvalidItemError(f"Tipo de objeto no válido: {value}. Solo se permite 'weapon' o 'armor'.")
    return normalized


def validate_color(value: str) -> str:
    """Acepta un color RGB hexadecimal, independiente del motor gráfico."""
    if not isinstance(value, str):
        raise ValidationError("El color debe ser un texto hexadecimal #RRGGBB.")
    color = value.strip().upper()
    if len(color) != 7 or color[0] != "#" or any(
        char not in "0123456789ABCDEF" for char in color[1:]
    ):
        raise ValidationError("El color debe tener el formato #RRGGBB.")
    return color
