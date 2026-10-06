from scripts.release_gate import REQUIRED, workflow_outcome


def runs(sha='reviewed'):
    return [{'id': i+1, 'name': name, 'head_sha': sha,
             'status': 'completed', 'conclusion': 'success'}
            for i, name in enumerate(sorted(REQUIRED))]


def test_gate_requires_all_successful_workflows_at_exact_sha():
    assert workflow_outcome(runs(), 'reviewed') == 'success'
    assert workflow_outcome(runs()[:-1], 'reviewed') == 'pending'
    assert workflow_outcome(runs('other'), 'reviewed') == 'pending'


def test_gate_fails_closed_on_failed_or_cancelled_checks():
    for conclusion in ('failure', 'cancelled', 'timed_out', 'skipped'):
        items = runs()
        items[0]['conclusion'] = conclusion
        assert workflow_outcome(items, 'reviewed') == 'failed'


def test_gate_uses_latest_attempt_and_waits_for_running_checks():
    items = runs()
    retry = dict(items[0], id=100, status='in_progress', conclusion=None)
    assert workflow_outcome([*items, retry], 'reviewed') == 'pending'
    retry.update(status='completed', conclusion='failure')
    assert workflow_outcome([*items, retry], 'reviewed') == 'failed'


def test_basin_scientific_validation_is_a_required_publication_gate():
    name = 'QTAIM basin Critic2 validation'
    assert name in REQUIRED
    items = [item for item in runs() if item['name'] != name]
    assert workflow_outcome(items, 'reviewed') == 'pending'
    items.append({'id': 100, 'name': name, 'head_sha': 'reviewed',
                  'status': 'completed', 'conclusion': 'failure'})
    assert workflow_outcome(items, 'reviewed') == 'failed'
