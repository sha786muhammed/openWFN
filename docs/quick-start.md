# Quick start

```bash
python -m pip install --pre --upgrade openwfn
openwfn examples install ./openwfn-examples
openwfn ./openwfn-examples/water.fchk summary
openwfn ./openwfn-examples/water.fchk geometry distance 1 2
openwfn ./openwfn-examples/water.fchk geometry angle 2 1 3
openwfn ./openwfn-examples/water.fchk orbitals frontier
openwfn ./openwfn-examples/water.fchk population mulliken
openwfn ./openwfn-examples/water.fchk density integrate
```

Create portable research artifacts:

```bash
openwfn ./openwfn-examples/water.fchk density cube water-density.cube
openwfn ./openwfn-examples/water.fchk report build water-report.html
```

Atom indices shown in commands are one-based. Coordinates are reported in ångströms, orbital energies in Hartree and eV, and ESP in Hartree/e.
