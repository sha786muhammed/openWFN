# Learning paths

The handbook offers three routes through the same scientific core. Move between
them whenever your work changes.

## Researcher path

1. Complete [Your first analysis](first-analysis.md).
2. Read [File formats](../formats.md) and confirm required records are available.
3. Study [Scientific methods](../methods.md), including units and assumptions.
4. Check the [Validation](../validation.md) status for the intended analysis.
5. Read [Limitations](../limitations.md), especially Experimental boundaries.
6. Build a [reproducible report](../tutorials/reports.md).
7. Record the exact version using [Citation](../citation.md).

## Student path

1. Learn the [core terminology](terminology.md).
2. Follow the [geometry tutorial](../tutorials/geometry.md).
3. Continue to [orbitals and density](../tutorials/orbitals-density.md).
4. Use the [workbench](../workbench.md) to connect numeric results with structure.
5. Read the corresponding method before interpreting a new quantity.
6. Compare each result with its validation evidence and limitations.

## Developer path

1. Install a development checkout with the test dependency group.
2. Review the [Python API](../python-api.md) and typed result model.
3. Read [File formats](../formats.md) before extending a parser.
4. Run the complete tests and active validation suite.
5. Keep scientific analysis separate from CLI, report, and workbench presentation.
6. Document new interfaces, assumptions, errors, validation, and capability status.

## Shared principle

Being able to run a command is not the same as knowing that its result is appropriate
for a scientific claim. Every path reconnects implementation, method, evidence, and
limitations.
