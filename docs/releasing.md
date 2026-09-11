# Releasing openWFN

This procedure prevents source, citation, GitHub, and PyPI versions from diverging. Every version-facing file and artifact for this release must identify openWFN 0.7.1.

## Release gates

1. Confirm that the working tree is clean:

   ```bash
   git status --short
   ```

2. Confirm that `[project].version` in `pyproject.toml` is `0.7.1`.

3. Verify citation metadata without modifying it:

   ```bash
   python scripts/sync_release_metadata.py --check
   ```

4. Run the complete test suite:

   ```bash
   pytest -v --cov=openwfn --cov-report=term-missing
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
   "$release_smoke/venv/bin/python" -m pip install dist/openwfn-0.7.1-py3-none-any.whl
   ```

7. Verify the installed version, console entry point, and reference workflow:

   ```bash
   "$release_smoke/venv/bin/python" -c "import openwfn; assert openwfn.__version__ == '0.7.1'"
   "$release_smoke/venv/bin/openwfn" --help
   "$release_smoke/venv/bin/openwfn" examples/water/water.fchk summary
   ```

8. Inspect the wheel and confirm that it contains all Python modules, `assets/3Dmol-min.js`, package metadata, the license, and the console entry point:

   ```bash
   unzip -l dist/openwfn-0.7.1-py3-none-any.whl
   ```

9. Commit the verified release state. Generated `dist/` and `build/` files remain untracked.

10. Create the annotated release tag:

    ```bash
    git tag -a v0.7.1 -m "openWFN 0.7.1"
    ```

11. Push the reviewed branch and tag only after explicit repository-owner approval.

12. Publish the artifacts that passed the preceding checks using the configured PyPI release mechanism. Do not rebuild after tagging; the published files must be the exact artifacts verified before the tag was created.

13. Verify PyPI from another clean environment:

    ```bash
    python -m pip install --no-cache-dir openwfn==0.7.1
    python -c "import openwfn; assert openwfn.__version__ == '0.7.1'"
    ```

14. Create or verify the GitHub release notes, confirm the public tag points to the reviewed commit, and add the approved repository topics through GitHub settings or the GitHub API.

## Historical 0.6.0 provenance

Do not create a historical `v0.6.0` tag unless the exact commit matching the published 0.6.0 wheel is proven. If provenance cannot be established, document the missing tag rather than manufacturing release history.
