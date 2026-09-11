"""Argument compatibility for reproducible v0.6.1 command lines."""


_GLOBAL_OPTIONS_WITH_VALUES = {"--output", "--format"}
_GLOBAL_FLAGS = {
    "--quiet",
    "--verbose",
    "--debug",
    "--no-color",
    "--plain",
    "--compact",
    "--overwrite",
    "--non-interactive",
}
_BATCH_OPTIONS_WITH_VALUES = {"--operation", "--workers", "--output-dir"}
_BATCH_FLAGS = {"--fail-fast"}


def _translate_file_help(arguments: list[str]) -> list[str]:
    """Make ``openwfn FILE --help`` display the root CLI help.

    With an optional root ``file`` positional before argparse subparsers, this
    two-token form is otherwise misread as though the file were a command.  Only
    the file-plus-help shape is rewritten; command-specific help is left alone.
    """

    translated = list(arguments)
    index = 0
    while index < len(translated):
        argument = translated[index]
        if argument in _GLOBAL_OPTIONS_WITH_VALUES:
            index += 2
            continue
        if argument in _GLOBAL_FLAGS:
            index += 1
            continue
        break

    if index + 2 != len(translated):
        return translated
    if translated[index].startswith("-") or translated[index + 1] not in {"-h", "--help"}:
        return translated

    return [*translated[:index], translated[index + 1]]


def _translate_command_first_batch(arguments: list[str]) -> list[str]:
    """Adapt ``openwfn batch INPUT ...`` to the legacy parser layout.

    The v0.7 root parser still places an optional ``file`` positional before the
    command subparser.  Batch is the one command whose natural interface starts
    with the command and then accepts one or more input files, so move the first
    batch input into the root ``file`` slot before argparse sees the arguments.
    Existing file-first invocations are left unchanged.
    """

    translated = list(arguments)
    index = 0
    while index < len(translated):
        argument = translated[index]
        if argument in _GLOBAL_OPTIONS_WITH_VALUES:
            index += 2
            continue
        if argument in _GLOBAL_FLAGS:
            index += 1
            continue
        break

    if index >= len(translated) or translated[index] != "batch":
        return translated

    input_index = index + 1
    while input_index < len(translated):
        argument = translated[input_index]
        if argument in _BATCH_OPTIONS_WITH_VALUES:
            input_index += 2
            continue
        if argument in _BATCH_FLAGS:
            input_index += 1
            continue
        if argument.startswith("-"):
            return translated
        break

    if input_index >= len(translated):
        return translated

    primary_input = translated[input_index]
    return [
        *translated[:index],
        primary_input,
        "batch",
        *translated[index + 1 : input_index],
        *translated[input_index + 1 :],
    ]


def translate_legacy_args(arguments: list[str]) -> list[str]:
    """Translate compatibility command forms to the v0.7 parser layout.

    Already-nested commands such as ``geometry angle`` and ``geometry dihedral``
    must pass through unchanged.  Re-translating their subcommand used to produce
    ``geometry geometry angle`` and made valid v0.7 command lines fail in argparse.
    """

    translated = _translate_file_help(arguments)
    translated = _translate_command_first_batch(translated)
    mapping = {"dist": "distance", "angle": "angle", "dihedral": "dihedral"}
    for index, argument in enumerate(translated):
        replacement = mapping.get(argument)
        if replacement is None or index == 0:
            continue
        if translated[index - 1] == "geometry":
            return translated
        return [*translated[:index], "geometry", replacement, *translated[index + 1 :]]
    return translated
