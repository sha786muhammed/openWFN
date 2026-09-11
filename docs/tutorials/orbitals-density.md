# Orbitals and density tutorial

```bash
openwfn water.fchk orbitals frontier
openwfn water.fchk density integrate --spacing 0.15 --padding 6
openwfn water.fchk density cube water-density.cube
openwfn water.fchk population mulliken
openwfn water.fchk population lowdin
```

Converge density integration with respect to both spacing and padding. Do not treat a visually smooth workbench surface as quantitative convergence evidence.
