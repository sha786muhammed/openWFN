"""Public exception hierarchy and stable command exit codes."""


class OpenWFNError(Exception):
    """Base class for an expected, user-facing openWFN failure."""

    exit_code = 1


class ParseError(OpenWFNError, ValueError):
    """The input could not be parsed safely."""

    exit_code = 3


class DataUnavailableError(OpenWFNError):
    """The requested calculation needs data absent from the input."""

    exit_code = 4


class ValidationError(OpenWFNError):
    """A scientific validation requirement was not met."""

    exit_code = 5


class ExternalProgramError(OpenWFNError):
    """A required external scientific program is unavailable or failed."""

    exit_code = 6
