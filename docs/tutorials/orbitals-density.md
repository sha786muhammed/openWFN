# Tutorial: orbitals and density with convergence checks

Electronic analyses require more FCHK records than geometry. Begin by asking the file what it contains.

## 1. Inspect and analyze

```bash
openwfn examples/water/water.fchk doctor
openwfn examples/water/water.fchk orbitals frontier
openwfn examples/water/water.fchk population mulliken
openwfn examples/water/water.fchk population lowdin
```

Record the spin channel, orbital indices, energies, and gap. The orbital-energy gap is not automatically an excitation energy. Differences between population schemes are expected because atomic charges are model-dependent partitions.

## 2. Converge total density

```bash
openwfn examples/water/water.fchk density integrate \
  --kind total --spacing 0.20 --padding 6.0
openwfn examples/water/water.fchk density integrate \
  --kind total --spacing 0.15 --padding 6.0
openwfn examples/water/water.fchk density integrate \
  --kind total --spacing 0.15 --padding 7.0
```

The integral should approach the molecular electron count. Choose settings based on convergence of the digits needed for the scientific conclusion; defaults are not universally sufficient.

## 3. Export a cube

```bash
openwfn examples/water/water.fchk density cube water-density.cube \
  --kind total --spacing 0.15 --padding 6.0
```

Cube files can be large and disclose coordinates and volumetric results. Record their controls and protect them as research data.

Read [Orbitals and density](../science/orbitals-density.md) and [Validation status](../science/validation-status.md) before interpreting results.
