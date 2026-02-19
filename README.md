# openWFN

![Tests](https://github.com/sha786muhammed/openWFN/actions/workflows/tests.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)

**openWFN** — *open WaveFunction Network* — is a lightweight, open-source
post-processing toolkit for **quantum chemistry wavefunction files**, focused on
accurate and transparent **molecular geometry analysis**.

It reads Gaussian formatted checkpoint files (`.fchk`) and provides essential
structural information directly from the command line or through an interactive
interface — without requiring heavy GUIs or complex visualization software.

openWFN is designed for **researchers, graduate students, and developers**
who want a scriptable and scientifically consistent geometry analysis tool.

---

## 🚀 Features (v0.3)

### 📂 File Handling
- Gaussian `.fchk` parsing
- Automatic `.chk → .fchk` conversion (via `formchk`)
- Internal unit conversion (Bohr → Å)

### 🧍 Molecular Information
- Atom index table (element symbols + coordinates)
- Molecular formula detection
- Center of mass calculation
- Charge and multiplicity extraction

### 📐 Geometry Calculations
- Distance between atoms
- Bond angle (i–j–k)
- Dihedral / torsion angle (i–j–k–l)
- Automatic bond detection (covalent radii based)

### 📦 Export
- XYZ export for visualization (VMD, Avogadro, PyMOL, etc.)

### 🖥 Interface Modes
- Command-line mode (scriptable, batch processing)
- Interactive menu mode (beginner-friendly)

---

## 🧠 Design Philosophy

openWFN focuses on:

- Unit consistency (Bohr → Å conversion handled internally)
- Transparent atom indexing
- Minimal dependencies
- Explicit, reproducible calculations
- Clean and readable source code

It is intentionally small, modular, and extensible.

---

## 📦 Installation

### Requirements
- Python ≥ 3.10
- Gaussian installed (optional, only required for `.chk` → `.fchk` conversion)

### Install from GitHub

```bash
git clone https://github.com/sha786muhammed/openWFN.git
cd openWFN
pip install -e .
```

---

## 🔧 Usage

### Interactive Mode

```bash
openwfn molecule.fchk
```

Menu:

```
1. Molecular information
2. Atom index table
3. Distance between two atoms
4. Bond angle (i–j–k)
5. Dihedral angle (i–j–k–l)
6. Export XYZ
7. Detect bonds
0. Exit
```

---

### Command-Line Mode

```bash
# Molecular information
openwfn molecule.fchk info

# Distance
openwfn molecule.fchk dist 1 5

# Angle
openwfn molecule.fchk angle 1 2 3

# Dihedral
openwfn molecule.fchk dihedral 1 2 3 4

# Bond detection
openwfn molecule.fchk bonds

# Export XYZ
openwfn molecule.fchk xyz molecule.xyz
```

---

## 📄 License

MIT License.

---

## 👤 Author

**Muhammed Shah Shaji**  
PhD Researcher — Computational Chemistry  

GitHub: https://github.com/sha786muhammed