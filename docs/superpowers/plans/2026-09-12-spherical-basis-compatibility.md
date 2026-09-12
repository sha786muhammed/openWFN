# Spherical Gaussian Basis Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace one-off 5D handling with a shared, validated Gaussian real-spherical basis layer supporting pure D/F/G/H shells throughout AO evaluation, overlap matrices, AO atom mapping, and downstream population analysis.

**Architecture:** Keep Cartesian primitive/contraction evaluation as the numerical foundation. Add a single spherical-shell transformation API that maps normalized Cartesian shell blocks to Gaussian-ordered real spherical shell blocks for `l=2..5`; reuse the same matrices for AO values and overlap block transforms. Keep unsupported pure shells explicit through `DataUnavailableError`.

**Tech Stack:** Python 3.10–3.13, NumPy, pytest, existing openWFN Gaussian FCHK model/parser/analysis stack.

**Spec:** `docs/superpowers/specs/2026-09-12-spherical-basis-compatibility-design.md`

## Global Constraints

- Validated pure spherical shells are exactly `l=2` (5D), `l=3` (7F), `l=4` (9G), and `l=5` (11H).
- Preserve Gaussian FCHK AO ordering for supported pure shells.
- Existing S/P/SP and Cartesian-shell behavior must remain unchanged.
- Never approximate a pure shell as a Cartesian shell with a different function count.
- Pure shells above `l=5` must fail explicitly with `DataUnavailableError`.
- No new runtime dependency is added for the transformation layer.
- PR #21 does not include REST APIs, GPU acceleration, ML, ECP-physics changes, or new population schemes.

---

### Task 1: Add RED regression tests for pure F/G/H shells and explicit higher-shell failure

**Files:**
- Modify: `tests/unit/test_basis.py`

**Interfaces:**
- Consumes: `evaluate_ao(basis, molecule, points_bohr) -> np.ndarray`, `overlap_matrix(basis, molecule) -> np.ndarray`, `ao_atom_indices(basis) -> tuple[int, ...]`.
- Produces: failing expectations that pure F/G/H shells are supported with counts 7/9/11 and pure `l=6` remains unsupported.

- [ ] **Step 1: Add parametrized function-count and atom-map regression test**

```python
@pytest.mark.parametrize(("momentum", "count"), ((3, 7), (4, 9), (5, 11)))
def test_pure_high_angular_momentum_shell_has_expected_function_count(momentum: int, count: int) -> None:
    basis = BasisSet((BasisShell(0, momentum, (1.0,), (1.0,), pure=True),))
    points = np.array(((0.2, 0.3, 0.4),))

    values = evaluate_ao(basis, _atom(), points)

    assert values.shape == (1, count)
    assert ao_atom_indices(basis) == (0,) * count
```

- [ ] **Step 2: Add one-center orthonormal-overlap regression test for F/G/H**

```python
@pytest.mark.parametrize(("momentum", "count"), ((3, 7), (4, 9), (5, 11)))
def test_pure_high_angular_momentum_overlap_is_orthonormal(momentum: int, count: int) -> None:
    basis = BasisSet((BasisShell(0, momentum, (1.0,), (1.0,), pure=True),))

    matrix = overlap_matrix(basis, _atom())

    np.testing.assert_allclose(matrix, np.eye(count), atol=1e-11)
```

- [ ] **Step 3: Add explicit unsupported pure-I-shell test**

```python
def test_pure_shell_above_h_is_explicitly_unsupported() -> None:
    basis = BasisSet((BasisShell(0, 6, (1.0,), (1.0,), pure=True),))

    with pytest.raises(DataUnavailableError, match="pure angular momentum 6"):
        evaluate_ao(basis, _atom(), np.zeros((1, 3)))
```

- [ ] **Step 4: Run RED tests**

Run:
```bash
pytest tests/unit/test_basis.py -q
```

Expected: existing 5D tests remain green; new F/G/H tests fail because the evaluator does not yet support these pure shells.

- [ ] **Step 5: Commit tests only**

```bash
git add tests/unit/test_basis.py
git commit -m "test: cover spherical f g h shells"
```

---

### Task 2: Introduce one shared spherical-shell transformation API

**Files:**
- Modify: `src/openwfn/analysis/basis.py`
- Test: `tests/unit/test_basis.py`

**Interfaces:**
- Produces: `_cartesian_powers(momentum: int) -> tuple[tuple[int, int, int], ...]`, `_spherical_transform(momentum: int) -> np.ndarray`, and `_evaluate_shell_cartesian(...) -> np.ndarray` or equivalent internal helpers.
- Transformation matrix shape: `(2 * momentum + 1, n_cartesian)` for pure `l=2..5`.

- [ ] **Step 1: Generalize Cartesian monomial ordering through H shells**

Replace the fixed `_CARTESIAN_POWERS` ceiling with a deterministic Gaussian-compatible generator for all `l<=5` used in this PR. Preserve the current exact order for S/P/D/F to avoid regressions.

Required ordering contract:
```python
# Existing order must remain byte-for-byte equivalent for l <= 3.
# For l=4 and l=5, define the source-program Cartesian ordering once and test it.
```

- [ ] **Step 2: Implement `_spherical_transform(momentum)` for l=2..5**

Use validated real-solid-harmonic coefficients in Gaussian FCHK order, with rows corresponding to the pure functions and columns to openWFN's Cartesian monomial order.

Function contract:
```python
def _spherical_transform(momentum: int) -> np.ndarray:
    """Return the Gaussian-ordered normalized Cartesian->real-spherical transform."""
```

For unsupported momenta, raise:
```python
raise DataUnavailableError(
    f"Pure angular momentum {momentum} is not supported; validated range is 2 through 5."
)
```

- [ ] **Step 3: Add transform-shape tests**

```python
@pytest.mark.parametrize(("momentum", "rows", "cols"), ((2, 5, 6), (3, 7, 10), (4, 9, 15), (5, 11, 21)))
def test_spherical_transform_shape(momentum: int, rows: int, cols: int) -> None:
    transform = basis_module._spherical_transform(momentum)
    assert transform.shape == (rows, cols)
```

- [ ] **Step 4: Run focused tests and verify GREEN for transform shape**

Run:
```bash
pytest tests/unit/test_basis.py -q
```

Expected: transform-shape tests pass; AO/overlap F/G/H tests may still fail until Tasks 3–4.

- [ ] **Step 5: Commit transformation foundation**

```bash
git add src/openwfn/analysis/basis.py tests/unit/test_basis.py
git commit -m "feat: add spherical transform foundation"
```

---

### Task 3: Route AO evaluation through the shared pure-shell transform

**Files:**
- Modify: `src/openwfn/analysis/basis.py`
- Test: `tests/unit/test_basis.py`

**Interfaces:**
- Consumes: `_spherical_transform(momentum)` and Cartesian shell evaluation.
- Produces: `evaluate_ao()` returning exactly `2*l+1` pure functions for l=2..5 in Gaussian order.

- [ ] **Step 1: Evaluate each non-SP shell into a Cartesian block**

For a shell, build:
```python
cartesian = np.column_stack(
    [
        _evaluate_contraction(displacement, shell.exponents, shell.coefficients, powers)
        for powers in _cartesian_powers(shell.angular_momentum)
    ]
)
```

- [ ] **Step 2: Transform pure shell blocks once**

For `shell.pure and shell.angular_momentum >= 2`:
```python
transform = _spherical_transform(shell.angular_momentum)
pure_block = cartesian @ transform.T
columns.extend(pure_block[:, index] for index in range(pure_block.shape[1]))
```

Cartesian shells continue to append the Cartesian block unchanged.

- [ ] **Step 3: Verify F/G/H AO-count tests now pass**

Run:
```bash
pytest tests/unit/test_basis.py -q
```

Expected: pure F/G/H AO-count and atom-map tests pass; overlap orthonormality may still fail until Task 4.

- [ ] **Step 4: Verify existing S/P/SP/Cartesian behavior**

Run:
```bash
pytest tests/unit/test_basis.py -q
```

Expected: all pre-existing basis tests remain green.

- [ ] **Step 5: Commit AO routing**

```bash
git add src/openwfn/analysis/basis.py tests/unit/test_basis.py
git commit -m "feat: evaluate pure spherical shell blocks"
```

---

### Task 4: Transform overlap shell blocks consistently and decouple atom mapping from Cartesian specs

**Files:**
- Modify: `src/openwfn/analysis/basis.py`
- Test: `tests/unit/test_basis.py`

**Interfaces:**
- Consumes: `_spherical_transform(momentum)`.
- Produces: pure-shell overlap blocks in the same convention used by AO evaluation and `ao_atom_indices()` counts that follow `BasisShell.n_functions`.

- [ ] **Step 1: Build Cartesian shell-to-shell overlap blocks**

Introduce an internal block routine with contract:
```python
def _cartesian_shell_overlap(shell_a, center_a, shell_b, center_b) -> np.ndarray:
    """Return normalized Cartesian AO overlap for one shell pair."""
```

It must reuse the existing primitive normalization, contraction scaling, and `_overlap_1d` logic rather than numerically integrating AO values.

- [ ] **Step 2: Apply left/right spherical transforms per shell pair**

For each shell pair:
```python
block = cartesian_block
if shell_a.pure and shell_a.angular_momentum >= 2:
    block = _spherical_transform(shell_a.angular_momentum) @ block
if shell_b.pure and shell_b.angular_momentum >= 2:
    block = block @ _spherical_transform(shell_b.angular_momentum).T
```

Place the resulting block into the global AO overlap matrix according to shell offsets.

- [ ] **Step 3: Rewrite `ao_atom_indices()` to use shell function counts directly**

```python
def ao_atom_indices(basis: BasisSet) -> tuple[int, ...]:
    return tuple(
        atom_index
        for shell in basis.shells
        for atom_index in (shell.atom_index,) * shell.n_functions
    )
```

This avoids representing pure functions as fake Cartesian function specs.

- [ ] **Step 4: Verify D/F/G/H one-center overlap tests**

Run:
```bash
pytest tests/unit/test_basis.py -q
```

Expected: one-center overlap matrices are identity within `1e-11` for 5D/7F/9G/11H.

- [ ] **Step 5: Commit overlap and mapping integration**

```bash
git add src/openwfn/analysis/basis.py tests/unit/test_basis.py
git commit -m "feat: support spherical overlap blocks"
```

---

### Task 5: Protect downstream population analysis and existing Cartesian behavior

**Files:**
- Inspect/modify only if needed: `src/openwfn/analysis/population.py`
- Modify: `tests/validation/test_population_reference.py` if a compact synthetic pure-shell regression belongs there
- Test: `tests/unit/test_basis.py`, `tests/validation/test_population_reference.py`

**Interfaces:**
- Consumes: corrected `overlap_matrix()` and `ao_atom_indices()`.
- Produces: Mulliken/Löwdin analyses that accept pure D/F/G/H without special-case logic in population code.

- [ ] **Step 1: Run focused population/reference tests before modifying population code**

Run:
```bash
pytest tests/validation/test_population_reference.py -q
```

Expected: no population-code changes are needed if it consumes overlap and AO mapping generically.

- [ ] **Step 2: Add a regression only if current coverage does not exercise a pure shell through population analysis**

Construct a minimal synthetic `CalculationData` fixture whose AO dimensions match a pure D or F shell and assert population analysis returns finite charges and preserves total electron count.

- [ ] **Step 3: Run population and basis tests**

Run:
```bash
pytest tests/unit/test_basis.py tests/validation/test_population_reference.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit downstream regression coverage**

```bash
git add tests/validation/test_population_reference.py src/openwfn/analysis/population.py
git commit -m "test: protect spherical population analysis"
```

Skip `src/openwfn/analysis/population.py` from the commit if it required no change.

---

### Task 6: Full repository verification and real-FCHK handoff

**Files:**
- No production change unless verification exposes a regression.
- Update: PR #21 description after verification.

**Interfaces:**
- Produces: evidence that the implementation is ready for real-file validation but not yet ready to merge until the user's `large_test.fchk` results are checked.

- [ ] **Step 1: Run full test suite**

Run:
```bash
pytest -q
```

Expected: zero failures.

- [ ] **Step 2: Run lint/quality command used by CI**

Run the repository's configured Ruff/quality command from `pyproject.toml`/workflow, then correct only issues introduced by this branch.

- [ ] **Step 3: Confirm GitHub Actions**

Required checks:
- `Tests and quality` -> success
- `Documentation` -> success
- `Security audit` -> success

- [ ] **Step 4: Update local test checkout instructions**

User commands:
```bash
cd ~/Desktop/openWFN-spherical-test
git pull origin fix/spherical-d-shells
pip install -e .
cd ~/Desktop/openwfn_large_test
openwfn large_test.fchk doctor
openwfn large_test.fchk summary
openwfn large_test.fchk orbitals frontier
time openwfn large_test.fchk population mulliken
time openwfn large_test.fchk population lowdin
```

- [ ] **Step 5: Validate real population output before merge**

Acceptance criteria:
- no spherical D/F/G/H compatibility exception;
- Mulliken and Löwdin produce finite per-atom values;
- sum of reported atomic charges is consistent with molecular charge `+1` within a numerical tolerance appropriate to formatted output;
- no NaN/Inf or gross electron-count mismatch.

- [ ] **Step 6: Keep PR #21 draft until real-file validation succeeds**

Do not merge on CI evidence alone.
