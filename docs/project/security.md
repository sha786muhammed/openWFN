# Security and data privacy

openWFN is designed for **local processing**. Analysis commands read files on your computer and do not require an openWFN cloud account or upload service. The generated viewer and workbench run from standalone HTML files.

## Protect private data

Checkpoint files, reports, cube files, tables, screenshots, and HTML workbenches may reveal unpublished geometries, energies, methods, or molecular identities. Store generated artifacts with the same access controls as the original research data. Inspect every artifact before making it public.

Do not include credentials, API tokens, license-server details, personal filesystem paths, hostnames, or private data in bug reports. Create a minimal synthetic or permission-cleared reproducer whenever possible.

## External software and browser behavior

- `.chk` conversion invokes Gaussian's external `formchk` executable when requested.
- `--open` asks the operating system to open a locally generated HTML artifact.
- Documentation may load its web theme and MathJax from the published site; scientific CLI computation remains local.

## Dependency and workflow controls

The repository uses pinned GitHub Actions, least-privilege workflow permissions, automated tests, documentation checks, and Trusted Publishing for PyPI. No publishing password is stored in the repository.

## Report a vulnerability

Do not disclose a suspected vulnerability in a public issue. Use GitHub's private security-advisory reporting channel for the repository. Include the affected version, impact, reproduction steps, and suggested mitigation if known—without real secrets or confidential molecular inputs.

Scientific disagreements or incorrect numerical results that do not expose a security weakness can use a normal issue with a shareable fixture.

