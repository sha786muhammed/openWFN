"""Optional isolated-process resource measurement and termination controls.

RSS is sampled for the process tree, not an OS allocation quota. Output can
overshoot between samples; post-exit checks also count final files. This module
performs no scientific analysis and is not exposed by the read-only MCP server.
"""
import os
import shutil
import signal
import subprocess
import time
from math import isfinite
from pathlib import Path


def run_resource_command(command: list[str], workspace: Path, *, timeout_seconds: float,
                         max_rss_bytes: int, max_output_bytes: int,
                         poll_seconds: float = .01, env: dict[str, str] | None = None) -> dict:
    """Run a trusted command with spooled logs and sampled tree-RSS/output monitoring."""
    for label, value in [('timeout', timeout_seconds), ('RAM', max_rss_bytes),
                         ('output', max_output_bytes), ('poll interval', poll_seconds)]:
        if isinstance(value, bool) or not isfinite(value) or value <= 0:
            raise ValueError(f'{label} budget must be positive and finite')
    try:
        import psutil
    except ImportError as exc:
        raise ImportError('Resource supervision requires openwfn[resources].') from exc
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    stdout, stderr = workspace/'stdout.log', workspace/'stderr.log'
    if stdout.exists() or stderr.exists():
        raise FileExistsError('Resource log files already exist; choose a fresh workspace.')
    def disk_bytes():
        total = 0
        for path in workspace.rglob('*'):
            try:
                if path.is_file() and not path.is_symlink():
                    total += path.stat().st_size
            except FileNotFoundError:
                pass
        return total
    initial_bytes = disk_bytes()
    if shutil.disk_usage(workspace).free < max_output_bytes:
        raise ValueError('Insufficient free disk space for the configured output budget.')
    peak, samples, status, reason = 0, 0, 'success', None
    started = time.perf_counter()
    with stdout.open('wb') as out, stderr.open('wb') as err:
        process = subprocess.Popen(command, cwd=workspace, stdout=out, stderr=err,
                                   env=env, start_new_session=(os.name == 'posix'))
        monitored = None
        tracked = {}
        def resolve_process():
            # /proc may expose host PIDs while Popen uses a nested namespace.
            if os.name == 'posix' and Path('/proc/self/status').exists():
                own_status = Path('/proc/self/status').read_text()
                host_parent = next(line.split()[1] for line in own_status.splitlines()
                                   if line.startswith('Pid:'))
                if int(host_parent) == os.getpid():
                    return psutil.Process(process.pid)
                for candidate in Path('/proc').glob('[0-9]*/status'):
                    try:
                        fields = dict(line.split(':', 1) for line in candidate.read_text().splitlines()
                                      if ':' in line)
                        namespace_ids = fields.get('NSpid', '').split()
                        if (namespace_ids and int(namespace_ids[-1]) == process.pid
                                and fields.get('PPid', '').strip() == host_parent):
                            return psutil.Process(int(candidate.parent.name))
                    except (OSError, ValueError, psutil.NoSuchProcess):
                        continue
                own_ids = next((line.split()[1:] for line in own_status.splitlines()
                                if line.startswith('NSpid:')), [])
                if len(own_ids) > 1:
                    raise psutil.NoSuchProcess(process.pid)
            return psutil.Process(process.pid)

        def alive(member):
            try:
                return member.is_running() and member.status() != psutil.STATUS_ZOMBIE
            except psutil.NoSuchProcess:
                return False

        def terminate():
            # Observed descendants may have escaped the original session.
            if os.name == 'posix':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    # Darwin can reject a group signal during parent-exit races.
                    # Still terminate our owned root and observed descendants.
                    if process.poll() is None:
                        process.kill()
            for member in reversed(list(tracked.values())):
                if not alive(member):
                    continue
                try:
                    if Path('/proc/self/status').exists():
                        own_ids = next(line.split()[1:] for line in
                                       Path('/proc/self/status').read_text().splitlines()
                                       if line.startswith('NSpid:'))
                        member_ids = next(line.split()[1:] for line in
                                          Path(f'/proc/{member.pid}/status').read_text().splitlines()
                                          if line.startswith('NSpid:'))
                        os.kill(int(member_ids[len(own_ids)-1]), signal.SIGKILL)
                    else:
                        member.kill()
                except (ProcessLookupError, FileNotFoundError, psutil.NoSuchProcess):
                    pass
            if os.name != 'posix' and monitored is not None:
                try:
                    monitored.kill()
                except psutil.NoSuchProcess:
                    pass
        try:
            try:
                monitored = resolve_process()
            except psutil.NoSuchProcess:
                pass
            while True:
                try:
                    members = ([monitored, *monitored.children(recursive=True)]
                               if monitored is not None else [])
                    for member in members:
                        tracked[member.pid] = member
                    rss = 0
                    for member in tracked.values():
                        try:
                            rss += member.memory_info().rss
                        except psutil.NoSuchProcess:
                            pass
                    peak = max(peak, rss)
                    samples += 1
                except psutil.NoSuchProcess:
                    pass
                elapsed = time.perf_counter()-started
                output_bytes = disk_bytes()-initial_bytes
                if peak > max_rss_bytes:
                    status, reason = 'memory_limit', 'Observed process-tree RSS exceeded budget.'
                elif output_bytes > max_output_bytes:
                    status, reason = 'output_limit', 'Output/log file bytes exceeded budget.'
                elif elapsed > timeout_seconds:
                    status, reason = 'timeout', 'Wall-clock deadline exceeded.'
                if status != 'success':
                    terminate()
                    process.wait()
                    break
                if process.poll() is not None:
                    survivors = [member for member in tracked.values()
                                 if member is not monitored and alive(member)]
                    if survivors:
                        status, reason = 'process_error', 'Command exited with live descendants; survivors terminated.'
                    terminate()
                    break
                time.sleep(poll_seconds)
        except BaseException:
            terminate()
            process.wait()
            raise
    output_bytes = disk_bytes()-initial_bytes
    if status == 'success' and output_bytes > max_output_bytes:
        status, reason = 'output_limit', 'Final output/log file bytes exceeded budget.'
    if status == 'success' and process.returncode != 0:
        status, reason = 'process_error', f'Command exited with code {process.returncode}.'
    if status == 'success' and peak == 0:
        status, reason = 'measurement_unavailable', 'No nonzero RSS sample was observed.'
    return {'status': status, 'reason': reason, 'returncode': process.returncode,
            'elapsed_seconds': time.perf_counter()-started,
            'peak_observed_rss_bytes': peak, 'rss_samples': samples,
            'output_bytes': output_bytes, 'timeout_seconds': timeout_seconds,
            'max_rss_bytes': max_rss_bytes, 'max_output_bytes': max_output_bytes,
            'poll_seconds': poll_seconds,
            'measurement_scope': 'sampled process-tree RSS; workspace output and spooled logs',
            'stdout_path': str(stdout), 'stderr_path': str(stderr)}
