# Command-line reference

```text
openwfn [GLOBAL OPTIONS] FILE COMMAND [COMMAND OPTIONS]
openwfn examples install DESTINATION [--overwrite]
```

Run `openwfn --help` or `openwfn FILE COMMAND --help` for the installed release's authoritative syntax. Global options such as `--format json` and `--input-format FORMAT_ID` go before the input path.

For interoperable inputs, install the appropriate optional extra and inspect capabilities before requesting analyses that may not be present in the source file:

```bash
openwfn molecule.molden capabilities
openwfn molecule.wfx orbitals frontier
openwfn calculation.out summary
```

A parser being able to read a file does not mean every analysis is available. Missing records fail explicitly rather than being reconstructed silently.

## Global options

| Option | Purpose |
|---|---|
| `--version` | Print the installed version without requiring a file |
| `--format table\|plain\|json\|csv` | Select result rendering |
| `--input-format FORMAT_ID` | Select a registered parser for an ambiguous input |
| `--output PATH` | Write supported rendered output to a file |
| `--quiet`, `--verbose`, `--debug` | Control diagnostic detail |
| `--no-color`, `--plain`, `--compact` | Control terminal presentation |
| `--overwrite` | Permit intentional replacement of an existing output |
| `--non-interactive` | Disable interactive behavior |

## Command families

These are the public top-level choices shown by `openwfn --help`.

| Command | Purpose |
|---|---|
| `examples` | Install packaged example inputs |
| `summary` | Summarize molecular identity and calculation state |
| `info` | Show detailed FCHK metadata |
| `dist` | Legacy distance command |
| `angle` | Legacy angle command |
| `dihedral` | Legacy dihedral command |
| `bonds` | Detect bonds with the covalent-radius heuristic |
| `xyz` | Legacy XYZ export |
| `formchk` | Invoke Gaussian's external checkpoint converter |
| `view` | Create a standalone local molecular viewer |
| `interactive` | Start the guided terminal interface |
| `graph` | Show molecular fragments |
| `geometry` | Run distance, angle, and dihedral operations |
| `population` | Run Mulliken or Löwdin population analysis |
| `bondorder` | Run Mayer AO bond-order analysis |
| `orbitals` | Inspect frontier orbitals, compositions, cubes, DOS, and PDOS |
| `excited` | Inspect source excited states, one state, or source transition dipoles |
| `vibrations` | Inspect source-reported vibrational modes or one normal mode |
| `spectra` | Generate IR, Raman-activity, or UV–Vis stick/broadened spectra |
| `density` | Integrate or export electron and spin density |
| `esp` | Evaluate supported electrostatic-potential components |
| `report` | Build a reproducible research report |
| `workbench` | Build the offline molecular workbench |
| `cube` | Export an electron-density cube |
| `convert` | Convert molecular structure formats |
| `export` | Export a registered result table |
| `plot` | Create a supported scientific figure |
| `batch` | Analyze multiple inputs |
| `validate` | Run the density-conservation check |
| `capabilities` | Report normalized component and analysis availability |
| `doctor` | Inspect input type and available capabilities |
| `properties` | Extract source-reported QC output properties with the optional cclib reader |

## Inspection and structure

| Command | Syntax | Result |
|---|---|---|
| `summary` | `openwfn FILE summary` | Complete molecular summary when data permit; partial structure summary otherwise |
| `info` | `openwfn FILE info` | Parsed source metadata |
| `doctor` | `openwfn FILE doctor` | Input kind and normalized capability report |
| `capabilities` | `openwfn FILE capabilities` | Component states and registered-analysis requirements |
| `bonds` | `openwfn FILE bonds` | Covalent-radius bond heuristic |
| `graph` | `openwfn FILE graph` | Connected molecular fragments |
| `geometry` | `geometry distance I J` | Interatomic distance in ångströms |
| `geometry` | `geometry angle I J K` | Three-atom angle in degrees |
| `geometry` | `geometry dihedral I J K L` | Signed four-atom dihedral in degrees |

CLI atom indices are one-based. Summary bonds and fragments use a geometry heuristic rather than authoritative quantum-chemical bond orders.

## Electronic analyses

| Command | Syntax and options | Status note |
|---|---|---|
| `orbitals` | `orbitals frontier [--spin alpha\|beta\|all]` | Requires MO energies; `all` reports both unrestricted channels and the true overall HOMO |
| `orbitals` | `orbitals composition`, `orbitals cube`, `orbitals dos`, `orbitals pdos` | Availability depends on the required wavefunction records |
| `bondorder` | `bondorder mayer [--threshold VALUE]` | Mayer status follows input diagnostics and the documented validation boundary |
| `population` | `population mulliken` or `population lowdin` | Requires AO density and overlap data; conservation failures return `partial` with warnings |
| `density` | `density integrate [--kind total\|alpha\|beta\|spin]` | Grid integration with explicit conservation diagnostics |
| `density` | `density cube OUTPUT [grid options]` | Generated grid keeps its actual success/partial and validation state |
| `esp` | `esp point X Y Z [--component COMPONENT] [--method integrals\|grid]` | Integral electronic/total ESP and explicitly selected grid route retain separate validation boundaries |
| `validate` | `openwfn FILE validate` | Runs the default total-density conservation check |

For unrestricted calculations, use the spin-complete selector when appropriate:

```bash
openwfn FILE orbitals frontier --spin all
```

The accepted selector is `--spin alpha|beta|all`. The alpha-only default remains for backward compatibility and warns when a beta channel is present.

Post-HF calculations do not silently imply a correlated density. When the parsed matrix is the SCF density, population and density results identify the **SCF density** source and warn accordingly. A scientifically usable but incomplete result is retained as `partial`; it is not promoted to a clean success.

The default density spacing is **0.15 bohr** with 6.0 bohr padding. These are starting values, not universal convergence settings.

## Excited states and UV–Vis

Excited-state analysis is **Experimental**. Gaussian, ORCA, and Q-Chem source adapters normalize source-reported state information into one typed job/state model while preserving program, method family/detail, source state identifiers, energies, oscillator strengths, transition dipoles, multiplicity, symmetry, contributions, and explicitly labelled amplitude conventions when available.

```bash
openwfn calculation.log excited states
openwfn --format json calculation.log excited state 2
openwfn calculation.log excited dipoles
openwfn calculation.log spectra uvvis --fwhm 0.20 --points 1501
openwfn calculation.log excited states --export states.csv
openwfn calculation.log spectra uvvis --export uvvis.svg
```

`excited states` lists source states. `excited state N` selects one one-based state from a source job. When a file contains multiple excited-state jobs, pass `--job N` to analyses that require one job. `excited dipoles` exposes only source-reported transition-dipole vectors; missing vectors are never inferred.

`spectra uvvis` preserves all source state/stick data and derives a deterministic Gaussian oscillator-strength profile in **energy space**. The visualization default is **0.20 eV FWHM**. Dark states with `f=0` remain valid source sticks. States with missing oscillator strength, negative oscillator strength, or nonpositive excitation energy remain visible in source data but are excluded from the simulated optical curve with explicit reasons; negative values are not silently clamped.

| Option | Meaning |
|---|---|
| `--job N` | One-based source excited-state job |
| `--fwhm EV` | Gaussian full width at half maximum; default 0.20 eV |
| `--min EV`, `--max EV` | Explicit excitation-energy range |
| `--points N` | Number of broadened-curve grid points |
| `--no-wavelength` | Omit wavelength-domain derived arrays |
| `--export PATH` | CSV, JSON, PNG, or SVG spectrum export |
| `--dpi N` | Raster resolution for PNG export |

The wavelength-domain curve is derived from the energy-domain profile with the energy-to-wavelength Jacobian; it is not the same numeric y-array with a relabelled x axis. The broadened profile is a visualization/post-processing quantity, not absorbance, molar extinction coefficient, or an experimental instrument model. Method-specific TDDFT, EOM, ADC, CI, multireference, spin-flip, and other source conventions remain explicitly labelled rather than being treated as interchangeable. See [Excited states and UV–Vis](../science/excited-states-uvvis.md).

## Vibrational spectroscopy

Vibrational spectroscopy is **Experimental** on this feature line. The native Gaussian text-output path preserves source values and does not infer unavailable observables.

```bash
openwfn frequency.log vibrations
openwfn --format json frequency.log vibrations mode 3
openwfn frequency.log spectra ir --fwhm 20 --points 2001
openwfn frequency.log spectra raman --fwhm 20 --export raman.svg
openwfn frequency.log vibrations --export modes.csv
```

`vibrations` reports source frequencies, imaginary-mode sign, symmetry when present, reduced masses, force constants, IR intensities, Raman activities, and whether Cartesian normal-mode vectors are available. `vibrations mode N` returns one one-based normal mode and its displacement vectors when present.

`spectra ir` and `spectra raman` preserve a source stick table and also generate a deterministic Gaussian-broadened visualization curve. Options are:

| Option | Meaning |
|---|---|
| `--fwhm CM-1` | Gaussian full width at half maximum; default 20 cm^-1 |
| `--min CM-1`, `--max CM-1` | Explicit wavenumber range |
| `--points N` | Number of broadened-curve grid points |
| `--export PATH` | CSV, JSON, PNG, or SVG spectrum export |
| `--dpi N` | Raster resolution for PNG export |

Imaginary modes remain signed and visible in mode/stick data; they are excluded from the broadened physical spectrum with an explicit warning. Missing IR or Raman source data fail explicitly.

Gaussian `Raman Activ` values are **Raman activities**, not laser- and temperature-dependent Raman intensities. openWFN does not silently convert activity to intensity because that requires additional physical assumptions and experimental conditions. See [Vibrational spectroscopy](../science/vibrational-spectroscopy.md).

## Source-reported output properties

The optional `properties` reader is separate from the wavefunction-analysis registry:

```bash
python -m pip install "openwfn[outputs]"
python -m openwfn.cli --format json calculation.out properties
```

It can expose geometry, charge/multiplicity, SCF energy, selected orbital energies, dipole, printed charges, and termination information when the source program and file contain them. Missing values remain missing. Printed atomic charges are not recalculated populations, and normal termination does not establish optimization convergence.

## Reports, exports, and visualization

| Command | Syntax | Output |
|---|---|---|
| `report` | `report build OUTPUT [--report-format html\|markdown] [--analyses LIST]` | Self-contained research report; spectroscopy and excited-state analyses render tables and inline spectra when requested |
| `workbench` | `workbench [OUTPUT] [--open]` | Offline interface; supported inputs add Vibrations and/or Excited States workspaces |
| `view` | `view [--save HTML] [--open] [--no-labels] [--style ballstick\|stick]` | Standalone molecular viewer |
| `xyz` | `xyz OUTPUT` | XYZ export |
| `convert` | `convert --to xyz\|pdb\|mol\|sdf --output PATH` | Structure conversion |
| `export` | `export frontier\|mulliken\|lowdin OUTPUT` | Registered result table selected by extension |
| `plot` | `plot frontier OUTPUT [--dpi N]` | Frontier-orbital figure |
| `formchk` | `formchk [OUTPUT]` | Calls Gaussian's external `formchk` utility |

Vibrational CSV is row-per-mode; excited-state CSV is row-per-state; spectrum CSV is row-per-grid point. JSON keeps the complete versioned `ResultRecord`, including units, validation status, warnings, and provenance. PNG/SVG spectrum figures are views of the same arrays rather than independent calculations.

## DOS and PDOS

`orbitals dos` and `orbitals pdos` are finite-molecule orbital-energy analyses, not vibrational or excited-state spectra. `--sigma` is in eV; `--energy-min`/`--energy-max` control the range; `--points` controls resolution; `--export` writes CSV/JSON/PNG/SVG. PDOS adds `--group-by atom|element|angular` and `--method lowdin|mulliken`. See [DOS/PDOS](../science/dos-pdos.md).

## Batch and guided mode

`batch` accepts files/directories, comma-separated `--analyses`, worker and output controls, deterministic manifests, resume fingerprints, format hints, and fail-fast behavior. The spin selector applies to a requested frontier analysis. Machine-readable records preserve `success`, `partial`, or failed status instead of discarding usable partial results.

`interactive` launches the guided terminal. With a file but no command, a terminal session enters guided mode; redirected input or `--non-interactive` defaults to `summary`. The guided interface includes **Analyze vibrations and spectra** for supported vibrational sources and routes to the same registered analyses as the CLI/Python/MCP surfaces.

With `--format json`, successful parsed commands emit one result envelope on stdout. Runtime/input failures use structured failure records where applicable and return a nonzero exit code. Help and argument-syntax errors remain ordinary text.

The hidden `mo` developer preview is intentionally outside the public command contract.
