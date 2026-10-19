from .base import Language, get_language, register
from . import en, de  # noqa: F401  (registers the built-in languages)

__all__ = ["Language", "get_language", "register"]
