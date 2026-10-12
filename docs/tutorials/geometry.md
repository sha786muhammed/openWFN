# Tutorial: verify a molecular geometry

Measure distances and angles using the packaged water example. Copy the
examples into a new folder first:

```bash
openwfn examples install ./openwfn-examples
```

You do not need a source checkout. Use the same steps with your own structure,
checking atom order before choosing atom numbers.

## 1. Establish identity

```bash
openwfn ./openwfn-examples/water.fchk summary
openwfn ./openwfn-examples/water.fchk info
```

Confirm formula, charge, multiplicity, energy, and atom count before measuring.

## 2. Check connectivity

```bash
openwfn ./openwfn-examples/water.fchk bonds
openwfn ./openwfn-examples/water.fchk graph
```

The bond heuristic should identify two O–H connections and one fragment. This is a structural sanity check, not a quantum bond-order result.

## 3. Measure the structure

```bash
openwfn ./openwfn-examples/water.fchk geometry distance 1 2
openwfn ./openwfn-examples/water.fchk geometry distance 1 3
openwfn ./openwfn-examples/water.fchk geometry angle 2 1 3
```

Atom numbers are one-based. In angle `2 1 3`, atom 1 is the vertex. Expect equal O–H distances for this symmetric example and a bent H–O–H angle.

## 4. Capture structured evidence

```bash
openwfn --format json --output water-summary.json \
  ./openwfn-examples/water.fchk summary
```

JSON avoids scraping decorated terminal text. Preserve the command, version, and fixture identity.

## 5. Export and inspect

```bash
openwfn ./openwfn-examples/water.fchk convert --to xyz --output water.xyz
openwfn ./openwfn-examples/water.fchk workbench water-workbench.html
```

XYZ preserves structure but not basis functions, orbitals, or density. Use the offline workbench only for optional spatial review and JSON for computation.

Ask whether charge, multiplicity, atom ordering, dimensions, and connectivity all match the intended system. Continue with the [geometry methods](../science/geometry-topology.md).
