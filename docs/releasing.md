# Releasing openWFN

This guide targets the current stable release line. Release publication always
requires explicit repository-owner approval; preparing a release branch or PR
does not itself publish, tag, or upload anything.

The release version comes from `[project].version` in `pyproject.toml`. Current
release notes must exist at `docs/releases/<version>.md`, and the dated changelog
and citation metadata must agree before publication.

## Release gates

1. Run the read-only repository preflight and confirm the working tree is clean:

   ```bash
   python scripts/check_repository.py --root .
   git status --short
   ```

2. Confirm the intended version in `pyproject.toml`, the matching dated
   `CHANGELOG.md` entry, `CITATION.cff`, citation guide, README, installation
   guide, security support table, validation manifest, and release notes.

3. Verify release metadata without silently rewriting it:

   ```bash
   python scripts/sync_release_metadata.py --check
   ```

4. Run static, documentation, scientific, and complete software checks:

   ```bash
   python -m ruff check src tests scripts
   python scripts/check_docs.py --root .
   python -m pytest --strict-markers
   python -m mkdocs build --strict
   python scripts/run_validation.py
   python scripts/run_interop_validation.py
   python scripts/run_external_benchmarks.py --repository-only
   ```

5. Run the bounded real-workflow resource matrix against the versioned source
   corpus. Command/resource success is not scientific validation; inspect the
   capability-specific reference results separately.

   ```bash
   python scripts/benchmark_resources.py \
     --examples-dir examples/everyday-qc \
     --output resource-report.json
   ```

6. Build and validate both distributions:

   ```bash
   python -m build
   python -m twine check dist/*
   ```

7. Install the wheel in a fresh virtual environment with the same extras used by
   the stable release workflow. Install the packaged examples and rerun the
   real-workflow matrix against the **installed** corpus rather than the source
   checkout:

   ```bash
   release_smoke="$(mktemp -d)"
   python -m venv "$release_smoke/venv"
   wheel_file="$(find dist -name '*.whl' -print -quit)"
   "$release_smoke/venv/bin/python" -m pip install "${wheel_file}[interop,resources]"
   "$release_smoke/venv/bin/openwfn" --version
   "$release_smoke/venv/bin/openwfn" examples install "$release_smoke/examples"
   "$release_smoke/venv/bin/python" scripts/benchmark_resources.py \
     --examples-dir "$release_smoke/examples/everyday-qc" \
     --output "$release_smoke/resource-report.json"
   ```

   The benchmark must contain exactly 99 records for eleven molecular inputs
   and nine prescribed workflows per input, with no nonzero-exit, timeout, or
   resource-limit failures. This still does not promote partial/Experimental
   scientific results.

8. Inspect the wheel and source distribution. Confirm that they contain the
   Python modules, vendored JavaScript and notices, project license, top-level
   water example, and the complete `example_data/everyday-qc/` corpus.

   ```bash
   python -m zipfile -l dist/openwfn-*.whl
   python -m tarfile -l dist/openwfn-*.tar.gz
   ```

9. Commit the verified release state. Generated `dist/`, `build/`, local smoke
   environments, and generated benchmark reports remain untracked.

## Approved stable publication workflow

The automated stable path is `.github/workflows/publish.yml`. It is intentionally
version-driven rather than hard-coded to one release number.

A repository-owner-approved main-branch commit whose **subject is exactly**
`release:<version>` starts the stable publication job. The workflow derives
`RELEASE_VERSION`, `RELEASE_TAG=v<version>`, and the release-note path from
`pyproject.toml`; it rejects a mismatched commit subject or missing release note.

Before any publication it:

1. requires the exact release commit's required CI checks;
2. runs `python scripts/sync_release_metadata.py --check`;
3. builds both distributions and runs `python -m twine check dist/*`;
4. installs the built wheel with `interop,resources` extras;
5. installs the packaged examples;
6. reruns all 99 real workflows against the installed eleven-molecule corpus.

Only after those gates pass does the workflow create the annotated tag, publish
to PyPI through OIDC trusted publishing, and create the GitHub Release for the
same exact commit.

The annotated tag remains equivalent to the manual form:

```bash
git tag -a v<VERSION> -m "openWFN <VERSION>"
```

Do not create or move a release tag outside the approved flow unless the owner
is deliberately performing a documented recovery operation.

## Public-package verification

Publication is not considered complete merely because upload succeeded. The
same workflow creates a second clean environment, downloads the exact release
from public PyPI with the interoperability and resource extras, installs its
packaged corpus, and reruns the same 99-workflow matrix:

```bash
python -m pip install --no-cache-dir --index-url https://pypi.org/simple \
  "openwfn[interop,resources]==<VERSION>"
openwfn examples install published-examples
python scripts/benchmark_resources.py \
  --examples-dir published-examples/everyday-qc \
  --output published-resource-report.json
```

This verifies what an outside researcher actually receives from PyPI. The
benchmark records the imported openWFN version and hashes of the imported Python
package rather than substituting hashes from the repository checkout.

## Historical provenance

Do not manufacture historical tags. If the exact source commit for an old
published artifact cannot be proven, document the provenance gap instead of
creating a tag retroactively.
