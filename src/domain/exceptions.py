class DomainError(Exception):
    """Base para errores controlados del dominio."""
    pass

class ValidationError(DomainError):
    """Error general de datos inválidos."""
    pass

class InvalidNameError(ValidationError):
    """Nombre vacío o compuesto solo por espacios."""
    pass

class InvalidStatError(ValidationError):
    """Estadística no entera o menor/equivalente al límite permitido."""
    pass

class InvalidItemError(ValidationError):
    """Tipo de objeto o bonificaciones inválidas."""
    pass

class InventoryError(DomainError):
    """Objeto ausente, duplicado o no equipable."""
    pass

class InvalidActionError(DomainError):
    """Acción incompatible con el estado actual."""
    pass