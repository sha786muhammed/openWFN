# Geometry and molecular topology

Measure distances, angles and dihedrals using the coordinates in your file.
Use geometry-based bonds and fragments to check connectivity; they are not
quantum-chemical bond orders.

## Distance

For Cartesian positions $\mathbf r_i$ and $\mathbf r_j$,

$$
d_{ij}=\lVert\mathbf r_i-\mathbf r_j\rVert_2.
$$

openWFN presents molecular distances in ångströms.

## Bond angle

For angle $i$–$j$–$k$, construct $\mathbf u=\mathbf r_i-\mathbf r_j$ and $\mathbf v=\mathbf r_k-\mathbf r_j$:

$$
\theta=\cos^{-1}\!\left(\frac{\mathbf u\cdot\mathbf v}{\lVert\mathbf u\rVert\lVert\mathbf v\rVert}\right).
$$

Degenerate vectors do not define an angle and should be treated as invalid geometry.

## Dihedral

The dihedral is a signed angle between two planes, calculated with `atan2`.
Its sign depends on atom order. Keep all four atom numbers with the result.

## Bonds and fragments

Bond detection is a geometric heuristic based on covalent radii and separation, not a quantum bond-order calculation. The resulting adjacency graph defines connected components reported as fragments. It is useful for structure checking, but unusual coordination, metals, weak interactions, and periodic systems may need domain-specific interpretation.

**Status:** geometric measurements and graph operations are Stable. Bond assignments are explicitly heuristic.
