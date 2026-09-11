"""Connectivity, fragments, and graph cycle analysis."""

from collections import deque

from ..model import Molecule


def _adjacency(molecule: Molecule) -> list[set[int]]:
    adjacent = [set() for _ in molecule.atoms]
    for bond in molecule.bonds:
        adjacent[bond.atom1].add(bond.atom2)
        adjacent[bond.atom2].add(bond.atom1)
    return adjacent


def fragments(molecule: Molecule) -> tuple[tuple[int, ...], ...]:
    adjacent = _adjacency(molecule)
    unseen = set(range(len(molecule.atoms)))
    components: list[tuple[int, ...]] = []
    while unseen:
        start = min(unseen)
        queue = deque([start])
        component: list[int] = []
        unseen.remove(start)
        while queue:
            atom = queue.popleft()
            component.append(atom)
            for neighbor in sorted(adjacent[atom] & unseen):
                unseen.remove(neighbor)
                queue.append(neighbor)
        components.append(tuple(sorted(component)))
    return tuple(components)


def _tree_path(first: int, second: int, parent: dict[int, int | None]) -> list[int]:
    first_ancestors: list[int] = []
    node: int | None = first
    while node is not None:
        first_ancestors.append(node)
        node = parent[node]
    second_ancestors: list[int] = []
    node = second
    while node not in first_ancestors:
        second_ancestors.append(node)
        node = parent[node]
        if node is None:
            raise ValueError("cycle endpoints are not in the same component")
    common = node
    first_path = first_ancestors[: first_ancestors.index(common) + 1]
    return first_path + list(reversed(second_ancestors))


def _canonical_cycle(cycle: list[int]) -> tuple[int, ...]:
    smallest = min(cycle)
    start = cycle.index(smallest)
    forward = cycle[start:] + cycle[:start]
    reversed_cycle = list(reversed(cycle))
    reverse_start = reversed_cycle.index(smallest)
    backward = reversed_cycle[reverse_start:] + reversed_cycle[:reverse_start]
    return min(tuple(forward), tuple(backward))


def cycle_basis(molecule: Molecule) -> tuple[tuple[int, ...], ...]:
    """Return a deterministic fundamental cycle basis for the molecular graph."""

    adjacent = _adjacency(molecule)
    parent: dict[int, int | None] = {}
    tree_edges: set[tuple[int, int]] = set()
    for root in range(len(adjacent)):
        if root in parent:
            continue
        parent[root] = None
        stack = [root]
        while stack:
            atom = stack.pop()
            for neighbor in sorted(adjacent[atom], reverse=True):
                if neighbor not in parent:
                    parent[neighbor] = atom
                    tree_edges.add(tuple(sorted((atom, neighbor))))
                    stack.append(neighbor)
    cycles = {
        _canonical_cycle(_tree_path(bond.atom1, bond.atom2, parent))
        for bond in molecule.bonds
        if tuple(sorted((bond.atom1, bond.atom2))) not in tree_edges
    }
    return tuple(sorted(cycles))
