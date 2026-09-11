"""Argument compatibility for reproducible v0.6.1 command lines."""


def translate_legacy_args(arguments: list[str]) -> list[str]:
    """Translate legacy geometry commands to the v0.7 nested command tree."""

    translated = list(arguments)
    mapping = {"dist": "distance", "angle": "angle", "dihedral": "dihedral"}
    for index, argument in enumerate(translated):
        replacement = mapping.get(argument)
        if replacement is not None and index > 0:
            return [*translated[:index], "geometry", replacement, *translated[index + 1 :]]
    return translated
