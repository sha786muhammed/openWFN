import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import pytest

from openwfn.batch import BatchRecord, _run_parallel


def jobs(count: int):
    return [(index, (Path(f"input-{index}.xyz"), ("summary",))) for index in range(count)]


class ImmediateExecutor:
    last = None

    def __init__(self, max_workers: int):
        self.submitted = 0
        ImmediateExecutor.last = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, function, argument):
        self.submitted += 1
        future = Future()
        future.set_result(function(argument))
        return future


def record(argument):
    path, _ = argument
    return BatchRecord(str(path), "success")


def test_parallel_scheduler_bounds_initial_submission() -> None:
    completed = _run_parallel(jobs(20), 2, runner=record, executor_factory=ImmediateExecutor)

    next(completed)

    assert ImmediateExecutor.last.submitted == 4


def test_parallel_scheduler_yields_completion_order() -> None:
    def delayed(argument):
        path, _ = argument
        if path.name == "input-0.xyz":
            time.sleep(0.15)
        return BatchRecord(str(path), "success")

    completed = list(
        _run_parallel(jobs(3), 2, runner=delayed, executor_factory=ThreadPoolExecutor)
    )

    assert completed[0][0] != 0
    assert sorted(index for index, _, _ in completed) == [0, 1, 2]


def test_parallel_scheduler_propagates_worker_crash() -> None:
    def crash(_argument):
        raise RuntimeError("worker crashed")

    with pytest.raises(RuntimeError, match="worker crashed"):
        list(_run_parallel(jobs(2), 2, runner=crash, executor_factory=ThreadPoolExecutor))
