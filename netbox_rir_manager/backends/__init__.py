from netbox_rir_manager.backends.base import RIRBackend

BACKENDS: dict[str, type[RIRBackend]] = {}


def get_backend(rir_name: str) -> type[RIRBackend]:
    """Get a backend class by RIR name."""
    try:
        return BACKENDS[rir_name]
    except KeyError as err:
        raise ValueError(f"Unknown RIR backend: {rir_name}. Available: {list(BACKENDS.keys())}") from err


def register_backend(backend_class: type[RIRBackend]) -> type[RIRBackend]:
    """Register a backend class."""
    BACKENDS[backend_class.name] = backend_class
    return backend_class
