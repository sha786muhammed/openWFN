# Molecular-orbital cubes (Experimental)

For a real Gaussian AO basis, the signed field is
`psi_i(r) = sum_mu C_mu,i chi_mu(r)` in bohr^-3/2. It is an amplitude;
its square is an orbital density. Overall phase has no physical significance.
The existing AO evaluator supplies source-normalized Cartesian/pure spherical
functions. IOData inputs undergo the existing recorded convention transforms.

Required data: isolated geometry, supported Gaussian basis and coefficients for
the selected spin channel. Public orbital numbers are **one-based**. `alpha`
uses the restricted channel on restricted inputs; absent beta fails explicitly.
HOMO/LUMO use occupations, with the same threshold and energy rule as frontier
analysis; HOMO selection also works when no virtual orbitals are supplied.

```bash
openwfn molecule.fchk orbitals cube --mo homo --output homo.cube
openwfn molecule.fchk orbitals cube --mo lumo --spin beta --output lumo-beta.cube --spacing 0.2 --padding 6
openwfn molecule.fchk orbitals cube --mo 25 --output mo25.cube
```

Spacing and padding are in **bohr**, matching density commands. The two-million
point grid limit is checked before allocation. AO evaluation uses bounded chunks.
Cube comments record MO, spin, spacing, padding and input hash. API/CLI results
retain parser provenance, orbital energy, occupation/source, grid shape, raw
`ao_metric_norm = c^T S c`, and `squared_amplitude_integral`.

```python
from openwfn import load
result = load('molecule.fchk').orbital_cube('homo.cube', mo='homo', spacing_bohr=.2)
print(result.as_dict())
```

Example result data: `{"mo_number": 5, "spin": "restricted",
"ao_metric_norm": 1.0, "squared_amplitude_integral": 0.9999}`.
The actual values depend on the input and quadrature settings. Coefficients
are never renormalized. A metric norm error above 1e-6 or grid error exceeding
0.5% of metric norm gives a warning and partial status. Refine both spacing and
padding before quantitative use; the default grid does not guarantee convergence.

Analytic normalized-Gaussian tests establish sign, amplitude and squared norm;
chunk equivalence and resource/error tests cover safety. Cross-format equivalence
is regression evidence, not an independent wavefunction reference. The method
remains Experimental pending broader independent orbital-field benchmarks.
Cube writes are excluded from the read-only registry/MCP interface.

Verification on 2026-10-02: 11 cube tests pass, including FCHK/Molden/MWFN/WFN/WFX
water amplitudes (1e-7 absolute tolerance, global phase allowed) and separate
GBasis 0.1.0 Cartesian/pure d-shell evaluations (1e-12 amplitude tolerance).
GBasis uses an explicit independently mapped ordering. These are synthetic
polarized spin-channel checks, not an external unrestricted molecular benchmark.
Full suite at this stage: 620 passed, 1 skipped; lint passed.
