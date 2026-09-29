# Third-party notices

openWFN includes the following third-party software. The openWFN MIT license
applies to project-owned code and assets; it does not replace the terms listed
for bundled third-party material.

## 3Dmol.js

- Upstream project: <https://github.com/3dmol/3Dmol.js>
- Local file: `src/openwfn/assets/3Dmol-min.js`
- Purpose: offline molecular rendering in standalone viewer and workbench HTML
- SHA-256: `c24a17b28f38a6fbde99cea746e2d7414da2c60efce65fa75d5293bed204e510`
- Version: version not recoverable from the bundled file
- License: BSD-3-Clause, with incorporated GLmol, Three.js, and jQuery notices
- Full license: `src/openwfn/assets/3Dmol-min.js.LICENSE.txt`

The bundled file's banner refers to `3Dmol-min.js.LICENSE.txt`. The full license
file included here is reproduced from the 3Dmol.js upstream `LICENSE` file. No
exact release or source revision is claimed because the bundled minified file
does not identify one and the available repository record does not prove one.

## qc-iodata

- Upstream project: <https://github.com/theochem/iodata>
- Distribution: `qc-iodata==1.0.1`
- Purpose: optional interoperability backend for reading additional quantum-chemistry and molecular file formats
- License: GPL-3.0-or-later
- Installation: optional, through `pip install "openwfn[interop]"`
- Bundling status: not vendored; installed separately as a Python dependency when the interoperability extra is requested

openWFN keeps qc-iodata behind an adapter boundary. Project-owned public APIs,
result schemas, provenance, and scientific capability decisions remain defined
by openWFN rather than by qc-iodata's internal Python objects.
