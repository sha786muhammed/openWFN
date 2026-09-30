# Roadmap

This roadmap describes directions, not commitments. No item is assigned a release or delivery date.
Work is accepted only when its design, tests,
documentation, provenance, and validation evidence are ready.

## Maintenance

- Keep supported environments, dependencies, packaging, and documentation clean.
- Improve diagnostics without changing scientific meaning silently.
- Preserve stable machine-readable contracts and migration guidance.

## Interoperability

- Maintain the pinned 25-format IOData ingestion contract with
  redistribution-safe fixtures and capability-based analysis gating.
- Expand cross-format validation from the current same-calculation water set
  to independent calculations, unrestricted cases, larger systems, and
  program/version variants.
- Investigate multi-record trajectories only with an explicit sequence model;
  do not silently reinterpret the single-record API.

## Validation

- Expand independent reference cases, including unrestricted and higher-angular-
  momentum examples.
- Publish tolerances, conventions, source procedures, and limitations with each
  validated result.

## Scientific methods

- Consider methods only after definitions, units, supported cases, reference
  evidence, and failure behavior are specified.
- Keep experimental work clearly separated from validated output.

## Service layers

- Consider remote APIs or tool integrations only after the local CLI and Python
  contracts are stable, secure, and suitable for unattended batch work.

Priorities may change as defects, validation evidence, and contributor capacity
change. Open a feature proposal to discuss a roadmap item before implementation.
