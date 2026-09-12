try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version(__name__)
    except PackageNotFoundError:
        __version__ = "unknown"
except ImportError:
    __version__ = "unknown"

from .priority import calculate_patient_priority

