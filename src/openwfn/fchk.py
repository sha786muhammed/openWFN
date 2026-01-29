def read_fchk(filepath):
    """
    Read a Gaussian formatted checkpoint (.fchk) file
    and return all lines as a list of strings.
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    return lines

