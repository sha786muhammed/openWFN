# Multiwfn analysis-reference procedure

Multiwfn is used only as an independently executed reference program. It is not an
openWFN dependency, and its binary, configuration, licensed material, and raw external
fixtures are not stored in this repository.

## Required run record

Run on the designated Linux validation host and record all of the following before any
case can become active:

- absolute path and SHA-256 of the executed binary;
- exact version printed by that binary;
- operating-system release, CPU architecture, and thread count;
- SHA-256 of the effective `settings.ini`;
- input-file SHA-256 and immutable source commit;
- SHA-256 of the reviewed standard-input procedure and complete transcript.

Do not infer the version from a download filename. Do not activate a case when the
program exits abnormally or when the transcript contains warnings that affect the
requested values.

## Reproducible execution

Create and review one plain-text standard-input file per Multiwfn version and analysis.
The reviewed sequence for this evidence is `multiwfn-analysis.in`; it lists orbitals,
prints Mulliken charges, and prints Löwdin charges. Keep menu selections in that file,
not in an undocumented interactive session. Execute
with fixed locale and thread count, preserving standard output and standard error:

```bash
export LC_ALL=C
export OMP_NUM_THREADS=1
Multiwfn INPUT.fchk < PROCEDURE.in > TRANSCRIPT.txt 2>&1
sha256sum INPUT.fchk PROCEDURE.in TRANSCRIPT.txt settings.ini
```

The exact menu selections are version-specific and must be copied from a successful,
reviewed interactive discovery run for the same installed version. Never reuse a menu
sequence merely because it worked with another release.

## Normalized evidence

Store only reviewed derived evidence when redistribution permits it. A reference JSON
record must contain `schema_version`, `program`, `program_version`, `input_sha256`,
`binary_sha256`, `settings_sha256`, `procedure_sha256`, `transcript_sha256`, platform
metadata, and a nonempty `metrics` list. Each metric records its name, value, unit,
printed precision, convention, and justified absolute tolerance.

For frontier orbitals, state spin channel, occupation rule, and whether printed orbital
indices are one-based. For Mulliken and Löwdin populations, compare atomic charges from
the same wavefunction and state the atom ordering. Tighten tolerances to printed
precision; never widen them to conceal an unexplained difference.

## Captured evidence

The restricted water and unrestricted LiH records were captured on NASAKY on
2026-09-24 with Multiwfn `3.8(dev)`, update date `2024-Oct-24`. The executed binary,
settings, procedure, and transcript hashes are recorded in
`validation/external/references/`. The run used four threads, `LC_ALL=C`, and
`OMP_STACKSIZE=1G`; it completed without runtime errors. Raw transcripts remain on the
validation host and are identified by immutable SHA-256 hashes rather than committed.

Tolerances follow the precision printed by Multiwfn: half a unit in the final printed
decimal place. Water charges were printed to eight decimals; unrestricted LiH charges
and orbital energies were printed to five decimals. No tolerance was widened beyond
that reporting precision.
