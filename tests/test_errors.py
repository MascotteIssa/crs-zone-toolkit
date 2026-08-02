"""Les exceptions du noyau ajoutées au Jalon J2 (ARCHITECTURE §5)."""

import pytest

from crs_zone_toolkit.core.errors import (
    CrsZoneError,
    EmptyLayerError,
    InvalidGeometryError,
    MissingCrsError,
)


@pytest.mark.parametrize("exc", [MissingCrsError, EmptyLayerError, InvalidGeometryError])
def test_exceptions_derivent_de_la_base(exc: type[Exception]) -> None:
    assert issubclass(exc, CrsZoneError)
    with pytest.raises(CrsZoneError):
        raise exc("message")


def test_exceptions_j3_derivent_de_la_base() -> None:
    from crs_zone_toolkit.core.errors import (
        OutputExistsError,
        TransformUnavailableError,
    )

    for exc in (OutputExistsError, TransformUnavailableError):
        assert issubclass(exc, CrsZoneError)
