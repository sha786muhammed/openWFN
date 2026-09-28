# Release history

## 0.8.1 — scientific correctness hardening

Version 0.8.1 strengthens the stable 0.8 interfaces against silent scientific errors. It adds source-faithful ECP/ghost nuclear charges, conservation enforcement, explicit density provenance, spin-complete unrestricted frontier analysis, ROHF classification, occupation-aware frontier selection, safer cube validation, Löwdin conditioning diagnostics, chunked density grids, and permanent regression coverage for these cases.

[Read the detailed 0.8.1 notes](../releases/0.8.1.md)

## 0.8.0 — stable analysis contracts

Version 0.8.0 promotes the tested 0.8 interfaces to a stable release. It adds
strict option and finite-value validation, makes high-level Python results
consistent and provenance-bearing, and clarifies public atom numbering and the
preferred automation API. Scientific capability labels remain scoped to their
documented validation evidence.

[Read the detailed 0.8.0 notes](../releases/0.8.0.md)

## 0.8.0a2 — installed examples and bounded batching

Version 0.8.0a2 makes the alpha easier to evaluate from a built wheel, bounds
parallel work for large collections, adds repeatable throughput evidence, and
avoids plotting imports during ordinary CLI startup. Scientific capabilities
and validation claims are unchanged.

[Read the detailed 0.8.0a2 notes](../releases/0.8.0a2.md)

## 0.8.0a1 — reproducible analysis contracts and resilient batching

Version 0.8.0a1 is an alpha release of the v0.8 foundation. It introduces the schema-2.0 calculation boundary, versioned result envelopes, named analysis execution, provenance-rich batch manifests, recursive discovery, CSV indexing, and crash-safe resume. It also establishes the redesigned documentation and unified project identity.

[Read the detailed 0.8.0a1 notes](../releases/0.8.0a1.md)

## 0.7.2 — spherical basis and workflow consistency

Version 0.7.2 adds Gaussian real spherical basis support through H shells (5D, 7F, 9G, 11H), makes molecular summaries consistently available through structured renderers, fixes dynamic MOL/SDF version metadata, adds configurable validation-grid controls, and restores clean checkpoint-conversion error handling.

[Read the detailed 0.7.2 notes](../releases/0.7.2.md)

## 0.7.1 — corrective release

Version 0.7.1 repaired CLI routing, offline-workbench JavaScript, overwrite guidance, and responsive documentation layout without changing the v0.7 scientific capability boundaries.

[Read the detailed 0.7.1 notes](../releases/0.7.1.md)

## 0.7.0 — analysis workbench

Version 0.7.0 introduced the typed calculation model, structured CLI output, nested geometry/orbital/population/density/ESP commands, batch processing, reproducible reports, expanded structure and table exports, and the standalone offline molecular workbench. It also added explicit Stable, Validated, Experimental, and Unsupported capability labels.

[Read the detailed 0.7.0 notes](../releases/0.7.0.md)

## 0.6.1 — maintenance and packaging

Version 0.6.1 synchronized package metadata, clarified checkpoint conversion, repaired Python 3.10 compatibility, and established tested wheel building and credential-free PyPI publication.

## Earlier releases

Versions 0.4.0–0.6.0 established FCHK parsing, molecular summaries, geometry and topology commands, XYZ export, interactive mode, and the standalone molecule viewer. Consult the repository tags for the exact source at each release.

## Versioning guidance

For research, record the exact version from `openwfn --version` and preserve the command and input checksum. The online handbook follows the current `main` branch; release notes describe version-specific differences.
