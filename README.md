# openWFN

![Tests](https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)

**openWFN** — *open WaveFunction Network* — is an open-source, lightweight
post-processing toolkit for **quantum chemistry wavefunction files**, focused on
**molecular geometry analysis**.

It reads Gaussian formatted checkpoint files (`.fchk`) and provides essential
structural information directly from the command line or through an interactive
menu — without requiring heavy GUIs or complex post-processing software.

openWFN is designed for **researchers, students, and developers** who want a
simple, transparent, and scriptable alternative to large multi-purpose tools.

---

## 🚀 Features (v0.2)

Current capabilities include:

- 📁 **Gaussian `.fchk` file parsing**
- 🔄 **Automatic `.chk → .fchk` conversion** (via `formchk`)
- 🧍 **Atom index table** with element symbols and Cartesian coordinates
- 📏 **Distance calculation** between any two atoms
- 📐 **Bond angle calculation** *(i–j–k)*
- 🔁 **Dihedral / torsion angle calculation** *(i–j–k–l)*
- 📌 **XYZ export** for visualization (VMD, Avogadro, PyMOL, etc.)
- 🖥 **Dual interface**
  - Command-line mode (scriptable, batch-friendly)
  - Interactive menu (beginner-friendly)

---

## 🧠 Background

Quantum chemistry calculations (DFT, HF, post-HF) contain rich structural
information inside checkpoint files. While many tools focus on visualization
or electronic analysis, **simple geometry extraction and inspection** often
requires heavy software or manual parsing.

openWFN focuses on **clarity and correctness**:

- Explicit atom indexing (no ambiguity)
- No hidden assumptions
- Results traceable directly to wavefunction output
- Minimal dependencies, maximum transparency

---

## 📦 Installation

### Requirements

- Python ≥ 3.9
- Gaussian installed *(for `formchk`, optional if `.fchk` already exists)*

### Install from GitHub (recommended)

```bash
git clone https://github.com/sha786muhammed/openWFN.git
cd openWFN
pip install -e .
````

---

## 🔧 Usage

### 1️⃣ Interactive mode (recommended)

```bash
openwfn molecule.fchk
```

or directly from a Gaussian checkpoint:

```bash
openwfn molecule.chk
```

This opens an interactive menu:

```
1. Molecular information
2. Atom index table
3. Distance between two atoms
4. Bond angle (i–j–k)
5. Dihedral angle (i–j–k–l)
6. Export XYZ
0. Exit
```

---

### 2️⃣ Command-line (scriptable) mode

```bash
# Distance
openwfn molecule.fchk --dist 1 5

# Bond angle
openwfn molecule.fchk --angle 1 2 3

# Dihedral angle
openwfn molecule.fchk --dihedral 1 2 3 4

# Export XYZ
openwfn molecule.fchk --xyz molecule.xyz
```

---

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and
distribute with attribution.

---

## 👤 Author

**Muhammed Shah Shaji**
PhD Researcher — Computational Chemistry

GitHub: [https://github.com/sha786muhammed](https://github.com/sha786muhammed)
