# Experimental validation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Include real generated molecular inputs and bounded independent evidence for every Experimental pathway, with explicit unresolved limits.

**Architecture:** Extend the existing optional PySCF validation runner, keeping references outside the runtime core. Save generated Molden inputs, checksums, comparisons and a coverage ledger in the repository. Exercise existing shared services rather than creating scientific implementations.

**Tech Stack:** PySCF 2.12.1, qc-iodata 1.0.1, cclib 1.8.1, NumPy, pytest.

**Spec:** User request to validate Experimental functionality with varied real examples; docs/project/everyday-qc-design.md.

## Global Constraints

- Keep methods Experimental until independent evidence supports a deliberate promotion.
- No missing data filled with invented results; preserve partial warnings.
- No changes to model schema, published version, scientific conventions or MCP write containment.
- All generated grids stay under existing two-million-point bound.

## Review Focus

- Charged and unrestricted inputs must preserve authoritative electron/spin counts.
- Cartesian Loewdin projections must not be compared across different AO normalization conventions.
- ESP points must avoid singularities; comparison is to analytic Coulomb integrals.
- A coarse-grid failure must remain partial rather than be hidden by successful pointwise checks.
- Visualization/output-reader coverage must not be called independent scientific validation.

## Task 1: Molecular example corpus

**Files:** scripts/validate_everyday_pyscf.py; tests/validation/test_everyday_pyscf.py; examples/everyday-qc/.

- [x] Extend the existing cases with CO2, ethanol, water dimer, triplet O2 and a charged species.
- [x] Run the existing reference comparisons on every case and retain actual Molden files with hashes, method, geometry and basis metadata.
- [x] Add checked-in corpus regression tests so core analyses can be exercised without rerunning SCF.

## Task 2: ESP and partial-density validation

**Files:** scripts/validate_experimental_esp.py; tests/validation/test_experimental_esp.py; validation/everyday-qc/esp-report.json.

- [x] Compare total/electronic/nuclear potentials at off-grid points with PySCF int1e_rinv analytic integrals at three bounded spacings.
- [x] Record charge integration and convergence histories; assert declared fine-grid tolerances, retain coarse partial diagnostics.
- [x] Run water, charged and open-shell molecules with trusted source densities.

## Task 3: Full Experimental coverage ledger

**Files:** docs/project/experimental-coverage.md; examples/everyday-qc/README.md; existing visualization/output-reader tests; docs/science/validation-status.md.

- [x] Exercise real workbench fields and verify serialization against the core; audit the unavailable legacy orbital preview and fail its old zero-field stub explicitly.
- [x] Verify real source output parsing against a printed-value reference; identify remaining program/data gaps.
- [x] Link existing malformed, incomplete-data and conservation regression tests; leave each incomplete evidence class explicit.
- [x] Run full tests, lint, docs, internal and interop validation; save reports, commit staged units and verify remote CI.
