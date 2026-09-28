# Security and data privacy

The repository [security policy](https://github.com/sha786muhammed/openWFN/blob/main/SECURITY.md)
is the authoritative source for supported versions and private vulnerability
reporting. Do not disclose a suspected vulnerability in a public issue.

## Local processing

openWFN analysis commands read files on your computer. They do not require an
openWFN cloud account or upload service. The generated viewer and Experimental
workbench run from standalone HTML files.

Checkpoint files, reports, cube files, tables, screenshots, and HTML workbenches
may reveal unpublished geometries, energies, methods, or molecular identities.
Store generated artifacts with the same access controls as the original data and
inspect them before publication. Treat every such artifact as private data until
you have confirmed it is safe to share.

Do not include credentials, API tokens, license-server details, personal paths,
hostnames, or confidential inputs in issues. Prefer a small synthetic or
permission-cleared reproducer.

## External behavior

- Binary `.chk` conversion invokes the external Gaussian `formchk` program.
- `--open` asks the operating system to open a local HTML artifact.
- Viewer and workbench files embed molecular data and the local rendering engine.
- The published documentation site may load its theme and MathJax resources;
  scientific CLI computation remains local.

Use the scientific-discrepancy issue form for numerical disagreements that do
not create a security risk.
