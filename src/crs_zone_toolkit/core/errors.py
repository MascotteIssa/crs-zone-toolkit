"""Hiérarchie d'exceptions du noyau (ARCHITECTURE §5).

La CLI traduit ces exceptions en codes de sortie (SPEC §10) ; le noyau, lui,
ignore les codes de sortie. Les avertissements ne sont JAMAIS levés (ils sont
portés par AnalysisResult.warnings) — seules les vraies erreurs le sont.

Les exceptions sont ajoutées au fil des jalons, quand un test les exige (TDD) :
UnknownRegionError arrive avec le chargeur de profils (J1).
"""


class CrsZoneError(Exception):
    """Base de toutes les erreurs levées par le noyau crs-zone-toolkit."""


class UnknownRegionError(CrsZoneError):
    """Profil de région inexistant ou invalide (ARCHITECTURE §5, code CLI 1)."""


class MissingCrsError(CrsZoneError):
    """CRS d'entrée absent et aucun --assume-crs fourni (ARCHITECTURE §5, code CLI 2)."""


class EmptyLayerError(CrsZoneError):
    """Couche vide — rien à analyser (ARCHITECTURE §5, code CLI 1)."""


class InvalidGeometryError(CrsZoneError):
    """Géométries irréparables (make_valid a échoué) (ARCHITECTURE §5, code CLI 1)."""


class OutputExistsError(CrsZoneError):
    """Fichier de sortie existant sans overwrite (ARCHITECTURE §5, code CLI 2)."""


class TransformUnavailableError(CrsZoneError):
    """Transformation de datum requise mais seule une transfo « ballpark » est
    disponible (grille NTv2 absente) (ARCHITECTURE §5, code CLI 1)."""


class LayerReadError(CrsZoneError):
    """Couche source illisible ou inexistante (ARCHITECTURE §5, code CLI 1)."""


class NonInteractiveError(CrsZoneError):
    """apply sans TTY ni --auto/--choice — levée par la CLI (ARCHITECTURE §5, code 2)."""
