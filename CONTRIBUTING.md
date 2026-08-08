# Contributing to openWFN

Thanks for your interest in improving openWFN.

openWFN is a lightweight command-line toolkit for molecular geometry, connectivity, and structure exploration from Gaussian checkpoint data. Contributions that improve reliability, documentation, chemistry workflows, and usability are welcome.

## Good First Contributions

Useful contribution areas include:

- bug fixes
- additional tests
- clearer error messages
- new geometry-analysis helpers
- parser robustness
- viewer improvements
- documentation and examples

## Development Setup

Clone the repository and install it in editable mode with test dependencies:

```bash
git clone https://github.com/sha786muhammed/openWFN.git
cd openWFN
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

Run the test suite:

```bash
pytest
```

## Contribution Workflow

1. Create a focused branch.
2. Make one logical change.
3. Add or update tests when behavior changes.
4. Run the test suite locally.
5. Update documentation for user-facing changes.
6. Open a pull request explaining what changed and why.

## Project Principles

Please try to keep openWFN:

- lightweight
- easy to install
- predictable from the command line
- explicit about chemistry calculations
- useful without requiring a large software stack

Avoid introducing heavy dependencies unless they provide a clear scientific or usability benefit.

## Reporting Bugs

When reporting a bug, include:

- openWFN version
- Python version
- operating system
- command that failed
- minimal input or reproduction steps when possible
- the complete error message

Please avoid uploading proprietary or sensitive molecular data. A small synthetic example is preferred when possible.

## Feature Ideas

Feature proposals are welcome. For larger changes, opening an issue before implementation can help keep the scope aligned with the project's lightweight design.

## License

By contributing, you agree that your contribution will be distributed under the project's MIT License.
