# ELF and LOL localization descriptors

openWFN provides Experimental pointwise evaluation of the electron localization
function (ELF) and localized orbital locator (LOL). These descriptors are
intended for analysis of an existing wavefunction. They do not change the
underlying electronic-structure method and they are not substitutes for QTAIM
critical-point or basin analysis.

## Shared kinetic-energy convention

Both descriptors use the positive-definite kinetic-energy density

$$
\tau(\mathbf r)=\frac{1}{2}\sum_i n_i\lvert\nabla\psi_i(\mathbf r)\rvert^2.
$$

The homogeneous-electron-gas reference is

$$
\tau_0(\rho)=\frac{3}{10}(3\pi^2)^{2/3}\rho^{5/3}
$$

for a restricted closed-shell total density, and

$$
\tau_{0,\sigma}(\rho_\sigma)=\frac{3}{10}(6\pi^2)^{2/3}\rho_\sigma^{5/3}
$$

for an individual alpha or beta spin density.

## ELF

For the supported real-wavefunction convention, openWFN evaluates the
von Weizsaecker kinetic-energy density

$$
\tau_W=\frac{\lvert\nabla\rho\rvert^2}{8\rho}
$$

and Pauli excess

$$
D=\tau-\tau_W.
$$

The Becke-Edgecombe ELF is then

$$
\mathrm{ELF}=\frac{1}{1+(D/\tau_0)^2}
             =\frac{\tau_0^2}{\tau_0^2+D^2}.
$$

A materially negative Pauli excess is not squared into an apparently valid ELF.
The point is retained as invalid and serialized as `null` with diagnostics. Tiny
negative values within the recorded numerical tolerance may be clamped to zero.

## LOL

The Schmider-Becke LOL used here is

$$
\mathrm{LOL}=\frac{\tau_0}{\tau_0+\tau}.
$$

Materially negative positive-definite KED is treated as invalid. Tiny negative
roundoff within the recorded numerical tolerance may be clamped to zero.

## Spin policy

`channel="total"` is accepted only when the input is demonstrably restricted
closed shell. For unrestricted or other open-shell data, request
`channel="alpha"` or `channel="beta"`. openWFN does not silently average or mix
spin definitions to manufacture a total ELF/LOL field.

## Numerical safeguards

The default density floor is `1.0e-12 electron/bohr^3`. Points at or below the
floor are reported as invalid rather than extrapolated into the density tail.
The default absolute and relative tolerances used only to distinguish tiny
negative numerical noise from material negative Pauli/KED values are
`1.0e-12` and `1.0e-10`, respectively. Every public result stores the active
thresholds and formula/convention labels so that a serialized result remains
interpretable without consulting source code.

Point requests use the same centralized real-space resource ceiling and
memory-bounded AO chunking as density derivatives and KED. A request above the
ceiling fails before AO evaluation.

## Python API

```python
from openwfn import load

calculation = load("water.fchk")
points = [[0.2, 0.1, 0.3], [0.5, -0.2, 0.4]]

elf = calculation.analyze("elf", points_bohr=points, channel="total")
lol = calculation.analyze("lol", points_bohr=points, channel="total")
```

The result contains the coordinates, localization values, validity mask,
density, KED, homogeneous-electron-gas reference, units, conventions,
thresholds and diagnostics. ELF additionally exposes the von Weizsaecker term
and Pauli excess.

## Validation status

ELF and LOL remain **Experimental**. Software regressions cover analytic kernels,
closed-shell factor-of-two behavior, alpha/beta spin handling, density-tail
masking, nonfinite input, negative Pauli/KED diagnostics, JSON-safe null output,
registry/API parity and resource ceilings.

Independent validation CI regenerates restricted, Cartesian, charged, diffuse
UHF and triplet-UHF PySCF wavefunctions. PySCF AO derivatives and density
matrices are used to reconstruct `rho`, `grad(rho)`, positive-definite `tau`,
ELF and LOL independently of the openWFN localization kernels, and the results
are compared at explicit off-nuclear points.

This evidence validates the named same-wavefunction cases only. It does not yet
justify a universal Stable/Validated scientific claim across correlated
densities, ECP/pseudopotential systems, complex orbitals, periodic systems,
very high angular momentum, arbitrary program/version combinations or every
published ELF/LOL convention.
