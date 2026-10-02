# Releasing openWFN

This guide targets the 0.10.0rc1 release candidate; 0.9.2 remains stable. Do not execute tagging or
publication steps without separate owner approval.

For a future release whose changelog entry is `Unreleased`,
`sync_release_metadata.py --check` verifies the citation against the latest
dated release. Source-version and citation-version differences are intentional
at this stage. Do not invent a release date to make them match.

## Release gates

1. Run the read-only repository preflight, then confirm that the working tree is
   clean:

   ```bash
   python scripts/check_repository.py --root .
   git status --short
   ```

2. Confirm that `[project].version` in `pyproject.toml` is `0.10.0rc1`.

3. Only after the release date is finalized, replace the `Unreleased` changelog
   heading with that approved date, synchronize `CITATION.cff`, and update the
   citation guide, installation pages, README, security support table, and
   release notes to the actual release details. Then check the metadata:

   ```bash
   python scripts/sync_release_metadata.py
   python scripts/sync_release_metadata.py --check
   ```

4. Run the static, documentation, scientific, and complete software checks:

   ```bash
   python -m ruff check src tests scripts
   python scripts/check_docs.py --root .
   python -m pytest --strict-markers
   python -m mkdocs build --strict
   python scripts/run_validation.py
   python scripts/run_external_benchmarks.py --repository-only
   ```

5. Build and validate both distributions:

   ```bash
   python -m build
   python -m twine check dist/*
   ```

6. Install the wheel into a newly created temporary virtual environment:

   ```bash
   release_smoke="$(mktemp -d)"
   python -m venv "$release_smoke/venv"
   "$release_smoke/venv/bin/python" -m pip install dist/openwfn-0.10.0rc1-py3-none-any.whl
   ```

7. Verify the installed version, console entry point, and reference workflows:

   ```bash
   "$release_smoke/venv/bin/python" -c "import openwfn; assert openwfn.__version__ == '0.10.0rc1'"
   "$release_smoke/venv/bin/openwfn" --help
   "$release_smoke/venv/bin/openwfn" examples install "$release_smoke/examples"
   "$release_smoke/venv/bin/openwfn" --format json --output "$release_smoke/summary.json" "$release_smoke/examples/water.fchk" summary
   "$release_smoke/venv/bin/openwfn" "$release_smoke/examples/water.fchk" orbitals frontier
   "$release_smoke/venv/bin/openwfn" "$release_smoke/examples/water.fchk" report build "$release_smoke/report.html"
   "$release_smoke/venv/bin/openwfn" "$release_smoke/examples/water.fchk" workbench "$release_smoke/workbench.html"
   ```

   Confirm the JSON result reports success and formula `H2O`. The report must be
   self-contained. The workbench must contain the 3Dmol.js attribution, retain
   its scoped `Stable` interface status and field-level partial warnings, and load no remote script.

8. Inspect the wheel and confirm that it contains all Python modules, the
   vendored JavaScript, its full license, `THIRD_PARTY_NOTICES.md`, the project
   license, packaged example and provenance summary, package metadata, and the
   console entry point:

   ```bash
   python -m zipfile -l dist/openwfn-0.10.0rc1-py3-none-any.whl
   python -m tarfile -l dist/openwfn-0.10.0rc1.tar.gz
   ```

   The source archive must also contain the repository citation, conduct,
   contribution, contributor, maintainer, roadmap, security, provenance, and
   third-party notice files.

9. Commit the verified release state. Generated `dist/` and `build/` files remain untracked.

10. Create the annotated release tag:

    ```bash
    git tag -a v0.10.0rc1 -m "openWFN 0.10.0rc1"
    ```

11. Push the reviewed branch and tag only after explicit repository-owner approval.

12. Publish a GitHub Release for the reviewed tag. The trusted-publishing
    workflow checks out that exact tag, verifies its version, rebuilds both
    distributions, runs `twine check`, and publishes them to PyPI without a
    repository token.

13. Verify PyPI from another clean environment:

    ```bash
    python -m pip install --no-cache-dir openwfn==0.10.0rc1
    python -c "import openwfn; assert openwfn.__version__ == '0.10.0rc1'"
    ```

14. Create or verify the GitHub release notes, confirm the public tag points to the reviewed commit, and add the approved repository topics through GitHub settings or the GitHub API.

## Historical 0.6.0 provenance

Do not create a historical `v0.6.0` tag unless the exact commit matching the published 0.6.0 wheel is proven. If provenance cannot be established, document the missing tag rather than manufacturing release history.

## Approved candidate publication

The owner-approved `release:0.10.0rc1` merge invokes a narrowly scoped job in
`.github/workflows/publish.yml`. It waits for the exact main commit's four CI
workflows, checks citation/version metadata, builds both distributions, installs
the wheel into a fresh environment and runs the real molecular resource matrix.
Only then does it create the annotated candidate tag and publish via existing
PyPI OIDC trust. It creates a GitHub prerelease and verifies the public PyPI
package in another clean environment. It does not automatically promote a
candidate to a stable release or publish arbitrary future versions.
