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

## IOData (optional interoperability backend)

- Distribution: `qc-iodata`
- Version pinned by openWFN 0.9 interoperability contract: `1.0.1`
- Upstream project: <https://github.com/theochem/iodata>
- Purpose: optional parsing backend for additional quantum-chemistry and molecular file formats
- License: GPL-3.0-or-later
- Installation: `pip install "openwfn[interop]"`
- Bundling status: not vendored or redistributed inside openWFN

IOData is an optional, separately installed dependency. openWFN-owned code and
public result contracts remain independent of IOData's internal Python objects.
