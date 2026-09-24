# Tutorial: verify a molecular geometry

This tutorial uses the public water fixture from a source checkout. Installed-package users can substitute their own `.fchk` path.

## 1. Establish identity

```bash
openwfn examples/water/water.fchk summary
openwfn examples/water/water.fchk info
```

Confirm formula, charge, multiplicity, energy, and atom count before measuring.

## 2. Check connectivity

```bash
openwfn examples/water/water.fchk bonds
openwfn examples/water/water.fchk graph
```

The bond heuristic should identify two O–H connections and one fragment. This is a structural sanity check, not a quantum bond-order result.

## 3. Measure the structure

```bash
openwfn examples/water/water.fchk geometry distance 1 2
openwfn examples/water/water.fchk geometry distance 1 3
openwfn examples/water/water.fchk geometry angle 2 1 3
```

Atom numbers are one-based. In angle `2 1 3`, atom 1 is the vertex. Expect equal O–H distances for this symmetric example and a bent H–O–H angle.

## 4. Capture structured evidence

```bash
openwfn --format json --output water-summary.json \
  examples/water/water.fchk summary
```

JSON avoids scraping decorated terminal text. Preserve the command, version, and fixture identity.

## 5. Export and inspect

```bash
openwfn examples/water/water.fchk convert --to xyz --output water.xyz
openwfn examples/water/water.fchk workbench water-workbench.html
```

XYZ preserves structure but not basis functions, orbitals, or density. Use the Experimental workbench only for optional spatial review and JSON for computation.

Ask whether charge, multiplicity, atom ordering, dimensions, and connectivity all match the intended system. Continue with the [geometry methods](../science/geometry-topology.md).
