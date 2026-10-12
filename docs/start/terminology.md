# Core terminology

Look up terms you see in commands and results. Each definition explains
how openWFN uses the term.

## Calculation

The data openWFN reads from one input file: structure, calculation details,
available wavefunction records and information about the source.

## Formatted checkpoint (`.fchk`)

A text representation produced by Gaussian's `formchk` utility. openWFN reads this
format directly. A binary `.chk` file is proprietary and must be converted externally.

## Atomic unit

A natural unit system used in electronic-structure theory. Energies are commonly
reported in hartree (`E_h` or a.u.); coordinates in checkpoint records may be stored
in bohr and converted to ångströms at the parser boundary.

## Basis function

A mathematical function used to expand molecular orbitals. openWFN evaluates the
supported contracted Cartesian Gaussian basis representation when required records
are present.

## Molecular orbital

A linear combination of basis functions described by coefficients, energy, and
occupation. The highest occupied and lowest unoccupied orbitals are called HOMO and
LUMO.

## Density matrix

A matrix representation used with basis functions to evaluate electron density and
population analyses. Total and spin density matrices can determine alpha and beta
components when the required records are available.

## Population analysis

A scheme for partitioning electrons among atoms. Mulliken and symmetric Löwdin
methods are model-dependent; their charges are not directly observable quantities.

## Electrostatic potential (ESP)

Potential at a point arising from nuclei, an atomic-charge model, electrons, or the
combined system. These variants are not interchangeable and have different status.

## Provenance

Information connecting a result to its input bytes, parser, software version,
parameters, method, and capability status.

## Capability status

File capabilities show which data and analyses are available. The separate
validation labels Stable, Validated, Experimental and Unsupported describe
interface support and scientific evidence. See [Validation](../science/validation-status.md).
