"""Publication-oriented scientific figures."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..analysis.orbitals import HARTREE_TO_EV, FrontierOrbitals
from .tables import ExportRequest


def write_frontier_diagram(frontier: FrontierOrbitals, request: ExportRequest):
    normalized = request.format.lower().lstrip(".")
    if normalized not in {"png", "svg"}:
        raise ValueError("Frontier diagrams support PNG and SVG formats")
    request.ensure_writable()
    homo_ev = frontier.homo_hartree * HARTREE_TO_EV
    lumo_ev = frontier.lumo_hartree * HARTREE_TO_EV
    with plt.rc_context({"svg.fonttype": "none", "font.size": 11}):
        figure, axis = plt.subplots(figsize=(5.2, 4.0), constrained_layout=True)
        axis.hlines(homo_ev, 0.15, 0.85, color="#176b87", linewidth=3)
        axis.hlines(lumo_ev, 1.15, 1.85, color="#c2416c", linewidth=3)
        axis.text(0.5, homo_ev, f"  HOMO {frontier.homo_index + 1}", va="bottom", ha="center")
        axis.text(1.5, lumo_ev, f"  LUMO {frontier.lumo_index + 1}", va="bottom", ha="center")
        axis.annotate(
            f"Gap = {frontier.gap_ev:.4f} eV",
            xy=(1.0, (homo_ev + lumo_ev) / 2),
            ha="center",
            va="center",
            color="#243447",
        )
        axis.set_xlim(0.0, 2.0)
        margin = max(abs(lumo_ev - homo_ev) * 0.25, 1.0)
        axis.set_ylim(homo_ev - margin, lumo_ev + margin)
        axis.set_xticks([])
        axis.set_ylabel("Energy (eV)")
        axis.set_title("Frontier orbital energies")
        axis.spines[["top", "right", "bottom"]].set_visible(False)
        figure.savefig(
            request.path,
            dpi=request.dpi,
            metadata={
                "Title": "openWFN frontier orbital energy diagram",
                "Description": "HOMO and LUMO energies with the energy gap in electronvolts",
                "Creator": "openWFN",
            },
        )
        plt.close(figure)
    return request.path
