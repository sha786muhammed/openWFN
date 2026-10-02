"""Read-only CI gate for the explicitly approved release commit."""
import argparse
import json
import os
import time
from urllib.request import Request, urlopen

REQUIRED = frozenset({
    'Tests and quality', 'Documentation', 'Security audit',
    'Offline workbench browser validation',
})


def workflow_outcome(runs, sha):
    selected = {}
    for run in runs:
        name = run['name']
        if run.get('head_sha') != sha or name not in REQUIRED:
            continue
        if name not in selected or run['id'] > selected[name]['id']:
            selected[name] = run
    if any(run['status'] == 'completed' and run['conclusion'] != 'success'
           for run in selected.values()):
        return 'failed'
    if set(selected) == REQUIRED and all(
        run['status'] == 'completed' and run['conclusion'] == 'success'
        for run in selected.values()
    ):
        return 'success'
    return 'pending'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, default=1200.)
    args = parser.parse_args()
    if not 0 < args.timeout <= 1200:
        raise ValueError('Release gate timeout must be within (0, 1200] seconds')
    repo, sha = os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_SHA']
    request = Request(
        f'https://api.github.com/repos/{repo}/actions/runs?head_sha={sha}&per_page=100',
        headers={'Authorization': f"Bearer {os.environ['GH_TOKEN']}",
                 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28'},
    )
    started = time.monotonic()
    while time.monotonic()-started < args.timeout:
        with urlopen(request, timeout=30) as response:
            outcome = workflow_outcome(json.load(response)['workflow_runs'], sha)
        print(f'Release CI gate: {outcome}', flush=True)
        if outcome == 'success':
            return
        if outcome == 'failed':
            raise RuntimeError('Release commit has failed workflow checks; publication stopped')
        time.sleep(15)
    raise TimeoutError('Release checks did not complete before the publication deadline')


if __name__ == '__main__':
    main()
