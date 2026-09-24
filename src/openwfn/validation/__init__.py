"""Scientific validation utilities with explicit evidence boundaries."""

from .convergence import ConvergenceResult, GridPoint, assess_convergence

__all__ = ["ConvergenceResult", "GridPoint", "assess_convergence"]
