# Quick start

```bash
openwfn water.fchk summary
openwfn water.fchk geometry distance 1 2
openwfn water.fchk geometry angle 2 1 3
openwfn water.fchk orbitals frontier
openwfn water.fchk population mulliken
openwfn water.fchk density integrate
```

Create portable research artifacts:

```bash
openwfn water.fchk density cube water-density.cube
openwfn water.fchk report build water-report.html
```

Atom indices shown in commands are one-based. Coordinates are reported in ångströms, orbital energies in Hartree and eV, and ESP in Hartree/e.
