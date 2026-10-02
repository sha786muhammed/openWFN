# Supported-workflow stabilization

User goal: stable, scientifically defensible implemented workflows with real
molecular tests and readable terminal/HTML results. Work autonomously, preserve
shared scientific services and resource safeguards, and keep missing data explicit.

## Numerical design

The spatial-grid ESP approximation is replaced as the public CLI/API default
by Gaussian Coulomb integrals. Dependency inspection found that GBasis 0.1.0's
Windows NumPy constraint excludes supported Python/platform combinations; it
therefore remains an independent reference dependency, not a new runtime mandate.
The native integral module reuses the normalized Cartesian contraction specs
and spherical transforms already used by openWFN overlap/density evaluation.

For primitive products, Gaussian integration over x/y/z is exact. Represent
1/r by its Laplace Gaussian integral and substitute u=t/sqrt(p+t²), yielding
a smooth one-dimensional integral on [0,1]. Evaluate with 64 and 96 Gauss–Legendre
nodes, scaled for large p|P-C|²; report their difference. The electronic value
is -Tr(P V). Test against closed-form normalized s Gaussians and PySCF analytic
int1e_rinv for every real corpus wavefunction, including Cartesian/pure and spin.
Keep nuclear singularities explicit. Bound point count, basis work and temporary
memory before evaluation. Retain an explicitly selected grid method with its
actual-grid conservation warnings; legacy direct-service calls retain that method.

## Interface design

Human output gets compact tables for composition, Mayer pairs and spectra,
while structured JSON remains complete. Guided workflows load the same normalized
input as CLI/API, expose spin/data choices, and use the shared ResultRecord renderer.
Reports and workbench are tested as generated artifacts. Browser tests inspect
actual offline JavaScript execution, measurements, fields and error handling.

## Status decisions

Promote supported successful paths only after independent numerical checks,
end-to-end parity and interface tests pass. Stable describes supported interfaces;
Validated identifies numerical evidence for the documented set. Partial/missing
or ill-conditioned inputs keep their diagnostics and are not relabelled successful.
No claim that arbitrary chemistry, unimplemented analyses or absent source data
have become validated. Model/result schemas and published release remain unchanged.

## Staged tasks and acceptance

1. Native Coulomb integral module: closed-form test first, then all 11 molecular
   PySCF comparisons at 1e-8 hartree/e plus supported high-l/reference checks.
2. CLI/API ESP dispatch, provenance and safety: shared values, finite electronic
   potential at grid/nuclear positions, physical nuclear singular errors.
3. Presentation/guided workflows: bounded human output, full JSON, real inputs,
   invalid/missing-data/cancel behavior, independent geometry/density checks.
4. Real full-workflow runner and browser artifact tests; save observed evidence
   and examples. Complete test suite, lint/docs, review and remote CI before
   making status changes. Record remaining support boundaries explicitly.

## Observed implementation boundary

Stages 1–3 now have numerical/reference and real terminal regression coverage.
Guided frontier selection retains its existing alpha behavior; the CLI/API expose
explicit beta/all channels. Browser installation was attempted and failed because
the downloaded Chromium archives were truncated. Therefore browser certification
and a blanket Stable workbench claim remain pending. Existing payload, embedded
field, measurement JavaScript and offline-export tests continue to run.
