import io

from openwfn.app import CommandContext, execute
from openwfn.errors import DataUnavailableError, ParseError


def test_expected_domain_error_uses_its_stable_exit_code() -> None:
    error_stream = io.StringIO()

    code = execute(
        lambda: (_ for _ in ()).throw(ParseError("bad input")),
        CommandContext(error_stream=error_stream),
    )

    assert code == 3
    assert error_stream.getvalue() == "Error: bad input\n"


def test_unavailable_data_returns_code_four_without_traceback() -> None:
    error_stream = io.StringIO()

    code = execute(
        lambda: (_ for _ in ()).throw(DataUnavailableError("coefficients missing")),
        CommandContext(error_stream=error_stream),
    )

    assert code == 4
    assert "Traceback" not in error_stream.getvalue()


def test_debug_mode_shows_traceback_for_unexpected_failure() -> None:
    error_stream = io.StringIO()

    code = execute(
        lambda: (_ for _ in ()).throw(RuntimeError("unexpected")),
        CommandContext(debug=True, error_stream=error_stream),
    )

    assert code == 1
    assert "Traceback" in error_stream.getvalue()
    assert "RuntimeError: unexpected" in error_stream.getvalue()
