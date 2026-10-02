# Everyday QC expansion: assessment and design

Baseline: openWFN 0.9.2, main commit 0991406. This document records the staged
project requested on 2026-10-02; it is not a claim that the roadmap is complete.

## Repository assessment

`CalculationData` schema 2.0 contains molecular geometry, Gaussian shells,
spin-resolved orbital energies/coefficients/occupations, total/spin AO density,
and parser provenance. It has no first-class vibrational or transition data.
IOData normalizes source AO conventions into the existing Gaussian ordering.
`analysis/basis.py` owns contracted normalization, Cartesian/pure transforms,
AO values and analytic overlap through H shells. `analysis/orbitals.py` already
contracts AOs with MO coefficients. `analysis/grids.py` rejects oversized grids
before allocation; density services bound AO temporaries by chunking.

`services.py` creates ResultRecords, while `analysis/registry.py` attaches input
provenance, timing and capability checks. Python, CLI, reports, batch and MCP
consume these services/registered analyses. The registry currently accepts
only names, not analysis parameters; exports are separate mutations. MCP is
read-only and confined to a data root. Keep cube writes outside its registry.
The existing population/ESP code propagates conservation and conditioning
warnings. Never bypass those safeguards.

Existing validation distinguishes independent Multiwfn evidence, independent
GBasis evaluations, analytic invariants, and cross-format regression. Passing
an implementation test does not extend the existing external evidence.

## Architecture

Reuse the normalized model, AO evaluator, overlap, grid and cube writer.
Put each new algorithm in a focused analysis module and each result adapter
in shared services. Add parameter support to registry/API in a backward-
compatible keyword-only form only when required; batch keeps named defaults
initially. Registry defaults must be deterministic, bounded, and read-only.
Cube output uses shared services and API provenance wrappers, not MCP.
Do not change model schema for MO cubes/composition/bond orders/spectra.

MO indices at public interfaces are one-based; scientific array indices remain
zero-based. Alpha refers to the restricted channel on restricted inputs;
requesting absent beta data fails. HOMO/LUMO retain the existing occupation
rule. Cubes contain signed amplitudes in bohr^-3/2, never orbital densities.
Grid integral of squared amplitude and analytic c^T S c are independent
normalization diagnostics, with partial results on failed tolerances.

Composition uses a named Löwdin or Mulliken convention. Löwdin weights are
(S^1/2 c)_mu^2 / (c^T S c); Mulliken weights c_mu(Sc)_mu / (c^T S c)
may be negative. Report raw norm and residual, rather than concealing invalid
coefficients through normalization. Shell grouping follows normalized AO maps.

Mayer uses total P and spin Q=Palpha-Pbeta: sum over interatomic AO pairs of
(PS)_mu,nu(PS)_nu,mu + (QS)_mu,nu(QS)_nu,mu. No factor-two shortcut.
Missing spin density on open-shell inputs must fail; no closed-shell assumption.
Diagonal atom entries are zero and row sums are diagnostics, not oxidation states.

DOS counts each spatial orbital once per supplied channel, without occupancy
weighting or an implicit restricted factor of two. Width is Gaussian sigma in
eV. PDOS uses explicitly named composition weights and must sum pointwise to
DOS. Report truncation and projection normalization diagnostics.

## Scientific gates and roadmap

Each numbered unit gets numerical tests, missing/malformed-data checks,
CLI/API parity, docs and a clean commit before the next begins.

1. MO cubes: signed field, alpha/beta, selectors, bounded chunking, provenance,
   closed-form normalized Gaussian and independent evaluator comparisons.
2. Composition: atomic/shell/angular partitions, c^TSc and overlap diagnostics.
3. Mayer: restricted/unrestricted formula and density-source/conservation checks.
4. DOS: bounded Gaussian energy grid, configurable sigma/range, JSON/CSV/plots.
5. PDOS: atom/element/angular channels, signed Mulliken caveat, sum rules.
6. Hirshfeld: first acquire licensed, versioned spherical neutral free-atom
   reference densities with method/basis/units/hashes and trustworthy reference
   charges. Decide core treatment for ECPs. Reject unsupported elements/ECPs,
   integrate on converged atom-centered quadrature, and record partition and
   charge closure. A hydrogenic proxy for all elements is prohibited.
7. Vibrations: additive typed records and source-faithful parser adapters;
   frequencies/modes/IR/Raman, units and imaginary-mode policy. Source Raman
   activities alone do not define a temperature/laser-dependent Raman intensity.
8. Excited states: additive typed records, energies/f/transition dipoles and
   explicitly defined amplitudes; UV-Vis with energy/wavelength Jacobians.
9. NTO: establish excitation convention (CIS/TDA vs full TDDFT X/Y), AO metric
   and spin blocks before SVD. Reject insufficient transition data.
10. Density derivatives: analytic Gaussian primitive derivatives, same pure
    transforms/normalization; compare analytic and independent finite differences.
11. QTAIM: bounded searches, residuals, Hessian classification, topology checks,
    bond paths; report incompleteness instead of claiming an exhaustive search.
12. ELF/LOL: document spin kinetic-energy conventions and numerical floors.
13. NCI: RDG/lambda2/sign(lambda2)rho, bounded cubes and provenance.
14. Basins: separate advanced project; converged zero-flux surfaces and integration.

Phase 2 is gated on stable Phase 1. An unavailable reference dataset or unresolved
scientific convention is recorded as blocked, not filled with an arbitrary method.

## Release policy

Preserve 0.9.2 metadata until review. Use separate PR-sized commits on a feature
branch. A 0.10.0a1 prerelease can expose explicitly Experimental Phase 1 methods;
0.10.0 requires reviewed independent references and complete documentation.
Subsequent spectroscopy and real-space work belongs in separately gated releases.
No PyPI publication or merge is part of numerical implementation verification.
