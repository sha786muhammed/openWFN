"""Legacy public stubs must never return plausible invented orbital fields."""
import numpy as np
import pytest

from openwfn.mo import evaluate_mo


def test_unimplemented_legacy_evaluator_is_explicitly_unavailable():
    with pytest.raises(NotImplementedError, match='evaluate_orbital'):
        evaluate_mo(np.array([[0., 0., 0.]]), 0, [1.], {}, [(0., 0., 0.)])
