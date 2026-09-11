"""Argument compatibility for reproducible v0.6.1 command lines."""


def translate_legacy_args(arguments: list[str]) -> list[str]:
    """Translate only legacy top-level geometry commands to the v0.7 command tree.

    Already-nested commands such as ``geometry angle`` and ``geometry dihedral``
    must pass through unchanged.  Re-translating their subcommand used to produce
    ``geometry geometry angle`` and made valid v0.7 command lines fail in argparse.
    """

    translated = list(arguments)
    mapping = {"dist": "distance", "angle": "angle", "dihedral": "dihedral"}
    for index, argument in enumerate(translated):
        replacement = mapping.get(argument)
        if replacement is None or index == 0:
            continue
        if translated[index - 1] == "geometry":
            return translated
        return [*translated[:index], "geometry", replacement, *translated[index + 1 :]]
    return translated
