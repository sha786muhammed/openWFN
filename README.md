# openWFN

**openWFN** — *open WaveFunction Network* — is an open-source, lightweight
post-processing toolkit for quantum chemistry wavefunction files, focused on
molecular geometry analysis.

It reads Gaussian formatted checkpoint (`.fchk`) files and provides useful
structural information directly from the command line.

This project is designed for researchers, students, and developers who work
with quantum chemistry data and want a simple but powerful geometry analysis
tool without the complexity of large multi-purpose software packages.

---

## 🚀 Features (v0.1)

The first release of openWFN includes:

- 📁 **`.fchk` file parsing** — robust extraction of molecular information  
- 🧍‍♂️ **Atom index table** — clear element symbols and 3D coordinates  
- 📏 **Distance calculation** between any two atoms  
- 📐 **Bond angle (i–j–k)** computation  
- 🔄 **Dihedral / torsion angle (i–j–k–l)** computation  
- 📌 **Export geometry to XYZ format** for visualization  
- 🖥 **Simple CLI interface** for quick and scriptable workflows  

---

## 🧠 Background

In computational chemistry, wavefunction data from quantum chemistry
calculations often contain rich structural information. Gaussian produces
binary checkpoint (`.chk`) files, which can be converted to formatted
checkpoint (`.fchk`) files for analysis.

openWFN fills a gap by offering a focused, lightweight toolkit for
geometry analysis directly from `.fchk` files, without requiring heavy GUIs
or complex post-processing environments.

---

## 📥 Installation

### Install from GitHub (recommended)

```bash
git clone https://github.com/sha786muhammed/openWFN.git
cd openWFN
pip install -e .

# Convert Gaussian checkpoint (.chk) to formatted checkpoint (.fchk)
formchk molecule.chk molecule.fchk

# Inspect molecular geometry
openwfn molecule.fchk

# Geometry analysis
openwfn molecule.fchk --dist 1 5
openwfn molecule.fchk --angle 1 2 3
openwfn molecule.fchk --dihedral 1 2 3 4

# Export to XYZ for visualization
openwfn molecule.fchk --xyz molecule.xyz

