# src/openwfn/graph.py

from typing import List, Tuple, Dict, Set

class MolecularGraph:
    """A lightweight representation of a molecular graph."""
    
    def __init__(self, num_atoms: int):
        self.num_atoms = num_atoms
        self.adj: Dict[int, Set[int]] = {i: set() for i in range(1, num_atoms + 1)}

    def add_edge(self, i: int, j: int, distance: float = 0.0) -> None:
        """Add an undirected bond between atom i and j (1-indexed)."""
        self.adj[i].add(j)
        self.adj[j].add(i)

    def get_neighbors(self, i: int) -> List[int]:
        """Get neighbors of atom i."""
        return sorted(list(self.adj.get(i, set())))

    def connected_components(self) -> List[List[int]]:
        """Find non-bonded fragments (connected components)."""
        visited = set()
        components = []

        for i in range(1, self.num_atoms + 1):
            if i not in visited:
                comp = []
                queue = [i]
                while queue:
                    curr = queue.pop(0)
                    if curr not in visited:
                        visited.add(curr)
                        comp.append(curr)
                        queue.extend(self.adj[curr] - visited)
                components.append(sorted(comp))
        
        return components


def build_graph(num_atoms: int, bonds: List[Tuple[int, int, float]]) -> MolecularGraph:
    """Build a MolecularGraph from a list of bonds."""
    graph = MolecularGraph(num_atoms)
    for i, j, d in bonds:
        graph.add_edge(i, j, d)
    return graph
