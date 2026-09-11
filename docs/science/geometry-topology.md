# Geometry and molecular topology

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

The four-atom torsion uses plane normals and a signed `atan2` construction. The sign depends on atom order; reversing the order can change it. Report all four indices with the result.

## Bonds and fragments

Bond detection is a geometric heuristic based on covalent radii and separation, not a quantum bond-order calculation. The resulting adjacency graph defines connected components reported as fragments. It is useful for structure checking, but unusual coordination, metals, weak interactions, and periodic systems may need domain-specific interpretation.

**Status:** geometric measurements and graph operations are Stable. Bond assignments are explicitly heuristic.

