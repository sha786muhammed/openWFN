# src/openwfn/graph.py

from collections import deque

class MolecularGraph:
    """A lightweight representation of a molecular graph."""
    
    def __init__(self, num_atoms: int):
        self.num_atoms = num_atoms
        self.adj: dict[int, set[int]] = {i: set() for i in range(1, num_atoms + 1)}

    def add_edge(self, i: int, j: int, distance: float = 0.0) -> None:
        """Add an undirected bond between atom i and j (1-indexed)."""
        del distance
        self.adj[i].add(j)
        self.adj[j].add(i)

    def get_neighbors(self, i: int) -> list[int]:
        """Get neighbors of atom i."""
        return sorted(self.adj.get(i, set()))

    def connected_components(self) -> list[list[int]]:
        """Find non-bonded fragments (connected components)."""
        visited: set[int] = set()
        components: list[list[int]] = []

        for i in range(1, self.num_atoms + 1):
            if i not in visited:
                comp: list[int] = []
                queue = deque([i])
                while queue:
                    curr = queue.popleft()
                    if curr not in visited:
                        visited.add(curr)
                        comp.append(curr)
                        queue.extend(self.adj[curr] - visited)
                components.append(sorted(comp))
        
        return components


def build_graph(num_atoms: int, bonds: list[tuple[int, int, float]]) -> MolecularGraph:
    """Build a MolecularGraph from a list of bonds."""
    graph = MolecularGraph(num_atoms)
    for i, j, distance in bonds:
        graph.add_edge(i, j, distance)
    return graph
