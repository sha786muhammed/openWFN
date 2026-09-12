# Spherical Gaussian Basis Compatibility Design

Date: 2026-09-12
Branch: `fix/spherical-d-shells`
PR: #21

## Goal

Replace the current one-off pure-d support with a shared, validated spherical-Gaussian compatibility layer so openWFN can analyze modern Gaussian FCHK calculations without failing one angular momentum at a time.

The immediate motivating case is a real `def2-TZVPP` FCHK where Mulliken/Löwdin progressed from failing at pure `l=2` after the first patch to failing at pure `l=3`. The new design should support the next commonly encountered pure shells in one coherent framework.

## Scope

Validated pure spherical shells:

- `l=2` -> 5D
- `l=3` -> 7F
- `l=4` -> 9G
- `l=5` -> 11H

Cartesian shells remain supported as they are today. Shells beyond the validated pure range must fail explicitly rather than silently producing scientifically questionable values.

## Scientific contract

1. Preserve Gaussian FCHK source-program AO ordering for every supported pure shell.
2. Use mathematically correct real-spherical transformations from the Cartesian primitive/contraction basis.
3. Apply the same transformation convention consistently in AO evaluation, AO overlap matrices, AO-to-atom mapping, and every downstream analysis that consumes those quantities.
4. Preserve normalization and orthogonality within numerical tolerance for one-center normalized shell tests.
5. Never approximate a pure shell by pretending it is the corresponding Cartesian shell with a different function count.
6. Keep unsupported angular momentum explicit and traceable through `DataUnavailableError`.

## Architecture

Introduce a single transformation layer in `openwfn.analysis.basis` rather than separate hard-coded branches for d, f, g, and h.

For each supported angular momentum, the layer should define or generate:

- Cartesian monomial ordering used by openWFN/Gaussian parsing
- Gaussian real-spherical ordering
- Cartesian-to-real-spherical transformation coefficients
- expected pure function count `2*l + 1`

`evaluate_ao()` should evaluate the normalized Cartesian contracted functions first and then transform the shell block to the pure representation when `shell.pure` is true.

`overlap_matrix()` should compute the Cartesian shell-block overlap and transform both sides into the pure representation. This avoids creating fake per-function Cartesian specifications for pure shells and keeps the transformation mathematically consistent with AO evaluation.

`ao_atom_indices()` should map `2*l+1` entries to the shell center for pure shells without depending on a Cartesian-only `_function_specs()` representation.

## Compatibility targets

The initial validation target is the real 9 MB `def2-TZVPP` Gaussian FCHK already used for stress testing. After implementation, the following must no longer fail because of pure d/f/g/h shells:

- Mulliken population analysis
- Löwdin population analysis
- AO evaluation paths used by density calculations
- overlap-dependent analyses

The design should also prepare openWFN for heavier-element and high-polarization basis sets that introduce G/H functions.

## Tests

TDD is required.

Add focused unit tests before each production change:

1. Pure D shell: 5 functions, Gaussian order, normalized overlap.
2. Pure F shell: 7 functions, Gaussian order, normalized overlap.
3. Pure G shell: 9 functions, Gaussian order, normalized overlap.
4. Pure H shell: 11 functions, Gaussian order, normalized overlap.
5. AO atom-index counts for every pure shell.
6. Explicit failure for pure shells above the validated range.
7. Regression tests confirming existing S/P/SP and Cartesian D/F behavior is unchanged.

Real-file validation after unit tests:

- `openwfn large_test.fchk doctor`
- `openwfn large_test.fchk summary`
- `openwfn large_test.fchk orbitals frontier`
- `openwfn large_test.fchk population mulliken`
- `openwfn large_test.fchk population lowdin`

For population results, verify numerical sanity in addition to successful execution: electron/charge totals should be consistent with the molecular charge and electron count within appropriate numerical tolerance.

## Non-goals for PR #21

Do not bundle the following into this change:

- REST/web API work
- GPU acceleration
- ML functionality
- ECP physics changes
- new population schemes
- unrelated parser rewrites
- arbitrary angular momentum with unvalidated conventions

Those can build on this basis compatibility layer later.

## Future follow-ons

After this PR is validated and merged, the next compatibility work should be handled separately:

1. open-shell and unrestricted population validation on transition-metal/Fe-S FCHK files;
2. ECP metadata and effective-electron accounting validation for heavy elements;
3. batch stress testing across many Gaussian FCHK files and basis families;
4. performance profiling of AO/grid evaluation with high-angular-momentum shells;
5. optional generalization beyond H only after reference conventions and regression fixtures are available.

## Success criteria

PR #21 is ready to merge only when:

- D/F/G/H pure-shell unit tests pass;
- the full existing test suite passes;
- documentation/security/quality CI passes;
- the real `def2-TZVPP` FCHK completes Mulliken and Löwdin without spherical-shell compatibility errors;
- population totals are numerically plausible and internally consistent;
- existing Cartesian/S/P/SP behavior shows no regressions.
