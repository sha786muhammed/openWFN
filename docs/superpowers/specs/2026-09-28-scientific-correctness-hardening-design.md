# Scientific Correctness Hardening Design

## Goal

Harden openWFN so scientifically incorrect or ambiguous wavefunction analyses do not silently return apparently successful results. The work must preserve the current public CLI/API where practical while making nuclear-charge semantics, electron-count validation, density provenance, spin handling, and result-status behavior explicit and testable.

## Scope

This design covers the correctness issues identified in openWFN 0.8.0 around ECP and ghost atoms, population and density conservation, post-HF density provenance, unrestricted and ROHF frontier-orbital behavior, cube validation, zero-spin density validation, ghost-aware structural summaries, occupation-aware frontier selection, and Löwdin overlap diagnostics.

The work includes regression tests and documentation. It does not redesign the entire analysis framework or add broad new quantum-chemistry functionality unrelated to these correctness risks.

## Design principles

1. Prefer authoritative data from the source FCHK file over values reconstructed from atomic numbers or assumptions.
2. Never present a numerically inconsistent scientific result as fully successful without a warning.
3. Preserve backward-compatible public entry points where possible.
4. Add explicit metadata and warnings rather than silently guessing.
5. Separate structural identity (`atomic_number`) from electrostatic/effective nuclear charge.
6. Treat spin channels and restricted-open-shell calculations explicitly.
7. Regression tests must reproduce every silent-wrong-result class fixed by this work.

## 1. Nuclear charge and ghost/ECP representation

### Problem

The current model stores only `Atom.atomic_number`. Population charges, nuclear ESP, expected electron counts, and cube headers therefore use the periodic-table atomic number even when the FCHK `Nuclear charges` record gives an effective value.

This is wrong for ECP calculations and ghost centers. For example, an ECP silicon center may have an effective nuclear charge of 4 rather than 14, while a ghost oxygen may have nuclear charge 0 rather than 8.

### Design

Extend the parsed atom representation with an optional effective nuclear charge field, named `nuclear_charge: float | None`.

For Gaussian FCHK input:

- Read the `Nuclear charges` array when present.
- Require its length to match `Number of atoms`.
- Set each atom's `nuclear_charge` from that record.
- If the record is absent, leave `nuclear_charge=None` and add a provenance warning indicating that atomic numbers will be used as a fallback where nuclear charge is required.

Provide one canonical helper for scientific nuclear charge lookup:

- use `atom.nuclear_charge` when present;
- otherwise use `float(atom.atomic_number)`;
- attach or propagate a warning when fallback data affects an analysis result.

`atomic_number` continues to represent element identity for symbols, basis-center identity, standard covalent radii, and ordinary structural export.

A ghost center is identified when the effective nuclear charge is approximately zero while its element identity or basis center remains present. Ghost status must not be inferred from atomic number alone.

## 2. Authoritative electron counts

### Problem

The current total expected electron count is reconstructed as `sum(atomic_number) - molecular_charge`. That is wrong for ECP and ghost systems.

### Design

For FCHK calculations, electron-count expectations use source records in this order:

- total: `Number of electrons`;
- alpha: `Number of alpha electrons`;
- beta: `Number of beta electrons`;
- spin: alpha minus beta.

If `Number of electrons` is absent, fall back to the sum of effective nuclear charges minus molecular charge. If effective nuclear charges are also unavailable, fall back to atomic numbers minus molecular charge and emit a warning.

The source of the expected count must be visible in result provenance or result data so users can determine whether it came from the file or a fallback.

## 3. Population analysis conservation enforcement

### Problem

Mulliken and Löwdin analyses currently compute `conservation_error` but still return `status="success"`, no warning, and `validation_status="Stable"` even when the error is large.

### Design

Use a central population conservation tolerance. Default acceptance target: `1e-6 e`, with normal well-conditioned results expected to be substantially smaller.

When `conservation_error <= tolerance`:

- status remains `success`;
- no conservation warning is added.

When `conservation_error > tolerance`:

- preserve the calculated values for diagnosis;
- set `status="partial"`;
- add a warning that includes the observed error and tolerance;
- downgrade `validation_status` from `Stable` to `Experimental` unless a more appropriate non-success status already applies.

Population atomic charges must use effective nuclear charges, not atomic numbers.

Batch execution must preserve the `partial` status and warnings rather than converting the result back to an apparently successful record.

## 4. Density conservation semantics

### Total, alpha, and beta density

Use the authoritative expected electron count described above. Validation should report both absolute and relative error where meaningful.

A total/alpha/beta density integration that exceeds the defined tolerance must not be labeled fully validated.

### Zero-spin density

For spin density, an expected integral of zero is valid. Relative error is undefined when the target is zero.

Therefore:

- when `abs(expected_spin) > epsilon`, use the normal relative-error rule;
- when `abs(expected_spin) <= epsilon`, validate against absolute error in electrons.

The result should report the error metric used (`relative` or `absolute`) so the interpretation is explicit.

## 5. Cube export validation

### Problem

The current total-density cube export labels total density as `Validated` solely because `kind == "total"`, without checking whether the generated grid actually integrates to the expected electron count.

### Design

A generated cube may be labeled `Validated` only if the same generated grid passes the density-conservation check for its density kind.

Otherwise:

- write the requested cube unless another hard error occurs;
- return `status="partial"` when validation fails;
- add a warning with the integration discrepancy;
- use `validation_status="Experimental"`.

The result includes the measured integral, expected integral, validation error, and the metric used.

## 6. Density provenance and post-HF calculations

### Problem

The parser currently stores `Total SCF Density` and `Spin SCF Density` without making that source explicit to the user. For MP2, CC, CI, or other post-HF calculations, users can therefore mistake an SCF reference density for a correlated density.

### Short-term design

Keep current SCF density behavior for backward compatibility, but make it explicit:

- density matrices carry a source/provenance label such as `scf`;
- density, population, ESP, and cube results include which density source was used;
- if the calculation method appears post-HF while an SCF density is used, add a warning naming the density source.

### Follow-on interface

Introduce density selection in a backward-compatible manner, with an eventual public option equivalent to `scf|post-scf`. This release must not claim post-SCF support unless the parser can identify and validate the relevant FCHK density record.

If a requested post-SCF density is unavailable, fail explicitly rather than silently falling back to SCF.

## 7. Unrestricted and ROHF orbital handling

### Unrestricted calculations

When beta orbitals are present, openWFN must treat alpha and beta as separate channels.

The high-level frontier summary for unrestricted data should be able to report:

- alpha HOMO/LUMO/gap;
- beta HOMO/LUMO/gap;
- the true overall HOMO as the occupied orbital with the higher energy across both spin channels;
- the spin channel of that overall HOMO.

Existing explicit `alpha` and `beta` requests remain supported.

Batch must provide a way to request spin-specific frontier analysis and must not silently imply that the default alpha frontier is the complete unrestricted frontier result.

### Restricted open-shell calculations

Do not classify every no-beta-energy calculation simply as `restricted`.

Use electron counts to distinguish at least:

- `restricted_closed_shell` when alpha and beta electron counts are equal;
- `restricted_open_shell` when alpha and beta counts differ and no separate beta channel is present;
- `unrestricted` when separate beta orbital data are present.

Expose that classification in orbital/result metadata.

## 8. Occupation-aware frontier selection

### Problem

The current frontier routine identifies the last occupied orbital and assumes the LUMO is exactly the next array entry.

### Design

Determine frontier orbitals from occupations and energies rather than adjacency alone:

- occupied candidates: occupation above a small occupation threshold;
- virtual candidates: occupation at or below the threshold;
- HOMO: highest-energy occupied candidate;
- LUMO: lowest-energy virtual candidate above the occupied manifold as represented by the source data.

For standard canonical ground-state files, results must remain unchanged.

The parser may continue to synthesize occupations from electron counts for ordinary FCHK files, but results must carry enough calculation/orbital classification metadata to make that assumption visible. Non-Aufbau/fractional-occupation cases that cannot be represented faithfully should be warned about or marked unsupported rather than silently forced into a standard filling pattern.

## 9. Ghost-aware structural summaries

### Problem

Summary calculations currently use atomic numbers for formula, center of mass, inferred bonding, and fragment counting. Ghost centers can therefore be treated as physical atoms.

### Design

For Gaussian calculations with explicit ghost centers:

- report the total number of centers and the number of physical nuclei separately;
- molecular formula excludes ghost centers;
- center of mass excludes ghost centers;
- inferred bond detection excludes ghost centers;
- fragment counting for physical molecular structure excludes ghost centers;
- include ghost-center count in summary data;
- add a warning when ghost centers are present so users know structural summaries were ghost-filtered.

The basis functions on ghost centers remain available for electronic-structure calculations.

## 10. Inferred bond provenance

FCHK does not provide authoritative molecular bond connectivity in the current parser path. Summary bond count and fragments are inferred from geometry/covalent radii.

Summary results must therefore identify the bond source explicitly, for example:

`bond_source: "covalent-radius heuristic"`

This avoids presenting inferred connectivity as authoritative chemistry. Unsupported or unusual bonding environments remain usable, but the heuristic nature is visible.

## 11. Löwdin overlap diagnostics

The current Löwdin implementation checks for significantly negative overlap eigenvalues but clips small negative values to zero. Add diagnostics for near-linear dependence.

At minimum, record the minimum overlap eigenvalue and an overlap condition indicator. When the overlap matrix is severely ill-conditioned, return the calculation with a warning and `status="partial"` rather than presenting the population as fully trustworthy.

The exact threshold must be centralized and regression-tested.

## 12. Result status and warning propagation

`ResultRecord` already supports `success`, `partial`, and `failed`.

Scientific validation failures that still yield diagnostically useful numbers should use `partial` rather than `failed`.

The registry, direct Python API, CLI rendering, and batch output must preserve result status and warnings. Source-level warnings and analysis-level warnings are merged without duplication.

A warning alone does not automatically imply `partial`; provenance/informational warnings may accompany `success`. A failed scientific consistency check does imply `partial`.

## 13. CLI/API compatibility

Preserve existing public calls where practical, including:

- `openwfn.load(...)`;
- `calc.orbitals("alpha"|"beta")`;
- `calc.population(...)`;
- `calc.density(...)`;
- existing CLI frontier, population, density, cube, ESP, and batch commands.

New metadata fields may be added to result data/provenance without removing existing fields.

Any new batch spin option should default in a way that does not silently misrepresent unrestricted calculations. If legacy behavior must be retained for compatibility, it must emit a warning when beta data are present but only alpha results are being produced.

## 14. Regression-test matrix

Add small, deterministic fixtures or generated test inputs covering each corrected behavior.

### Required regression cases

1. **ECP fixture**
   - effective nuclear charge differs from atomic number;
   - population charges use effective nuclear charge;
   - expected electron count uses FCHK electron count;
   - nuclear ESP and cube header use effective nuclear charge.

2. **Ghost-center fixture**
   - ghost nuclear charge is zero;
   - population/ESP do not assign physical nuclear charge to the ghost;
   - formula, center of mass, inferred bonds, and fragment count exclude the ghost;
   - basis data on the ghost remain usable.

3. **Population conservation failure fixture**
   - deliberately inconsistent density/population result;
   - `conservation_error` exceeds tolerance;
   - result has warning and `status="partial"`;
   - batch preserves partial status.

4. **ROHF/open-shell restricted fixture**
   - alpha and beta electron counts differ;
   - no separate beta orbital channel;
   - orbital classification is `restricted_open_shell`;
   - density/electron validation uses source electron counts.

5. **UHF fixture with beta HOMO above alpha HOMO**
   - both spin channels are reported correctly;
   - overall HOMO is identified as beta;
   - explicit alpha and beta requests remain correct;
   - batch does not silently report alpha as the complete frontier result.

6. **Post-HF fixture**
   - method metadata identifies MP2/CC/CI-like calculation;
   - SCF density usage is explicitly labeled and warned;
   - no claim of correlated density unless a supported post-SCF record is selected.

7. **Closed-shell singlet spin-density fixture**
   - expected spin integral is zero;
   - validation uses absolute error;
   - valid near-zero integral succeeds instead of raising because the expected value is zero.

8. **Cube validation fixture**
   - an accurate grid can be `Validated`;
   - an intentionally coarse/truncated grid is written but returned as `partial`/`Experimental` with warning.

9. **Near-linear-dependent Löwdin fixture**
   - overlap diagnostic crosses the warning threshold;
   - result is `partial` with a meaningful warning.

10. **Standard water/benzene regression**
    - existing ordinary closed-shell results remain unchanged within current numerical tolerances.

### Assertions

Across relevant fixtures, assert:

- atomic charges sum to molecular net charge within tolerance when the source data are consistent;
- integrated total density matches authoritative expected electron count within the configured validation tolerance;
- spin-channel integrals match alpha/beta expectations;
- ECP/ghost nuclear charges propagate consistently into all electrostatic outputs;
- warnings and `partial` statuses appear exactly when expected;
- no non-finite values are introduced into `ResultRecord` data;
- existing JSON/result schema remains readable.

## 15. Documentation changes

Update README and Python/CLI reference documentation to state:

- effective nuclear charge semantics for ECP and ghost centers;
- electron-count source and fallback behavior;
- population conservation tolerance and partial-result behavior;
- SCF versus post-SCF density provenance;
- unrestricted and restricted-open-shell frontier semantics;
- density/cube validation meaning;
- inferred-bond heuristic provenance;
- currently unsupported or unvalidated cases.

Do not label population analysis universally `Stable` unless the documented supported cases and validation behavior justify that label.

## 16. Performance and grid memory

The correctness changes above take priority. Grid evaluation should also be refactored to support chunked AO/density evaluation so large grids do not require one monolithic point-by-basis array in memory.

Chunking must be numerically equivalent to the unchunked calculation within floating-point tolerance.

The default spacing of 0.15 bohr should not be made finer blindly because that can greatly increase memory/runtime. Instead:

- document the accuracy/performance tradeoff;
- validate defaults against regression systems;
- consider adaptive/finer defaults only after benchmark evidence.

## 17. Non-goals for this pass

This pass does not attempt to:

- implement every Gaussian density record or every post-HF method;
- replace the FCHK parser with a general Gaussian log parser;
- provide authoritative bond orders/connectivity from FCHK where none are available;
- guarantee support for arbitrary fractional-occupation or excited-state SCF files without source data sufficient to reconstruct occupations;
- redesign the complete public API.

## Success criteria

The hardening pass is complete when:

1. Every required regression case above has a test that fails on the pre-fix behavior and passes after the fix.
2. ECP and ghost systems use effective nuclear charges consistently.
3. Electron conservation failures can no longer return silently as clean `success` results.
4. Post-HF calculations explicitly identify the density source used.
5. Unrestricted calculations cannot silently present alpha-only frontier information as the complete frontier result.
6. Zero-spin density validation works correctly.
7. Cube validation status is evidence-based.
8. Ordinary water/benzene workflows remain backward-compatible and numerically stable.
9. Full unit, integration, CLI, scientific-validation, and platform CI suites pass before merge.
