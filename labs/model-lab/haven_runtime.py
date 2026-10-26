"""Two prepared Linux runtimes. Fixed user unit; no install, download or shell."""
import http.client
from pathlib import Path
import sys
import threading
import time

import gpu_lease

STRATA = gpu_lease.STRATA_UNIT
_status_lock = threading.Lock()
_status_at = 0
_status_value = {}


def status():
    global _status_at, _status_value
    if sys.platform != 'linux':
        return {'supported': False}
    with _status_lock:
        if time.monotonic() - _status_at > 3:
            try:
                peers = gpu_lease.peer_busy()
                _status_value = {'supported': True, 'peer_busy': bool(peers),
                                 'strata_state': gpu_lease.unit_state(STRATA)}
            except Exception:
                _status_value = {'supported': True, 'peer_busy': True,
                                 'error': 'Cannot verify GPU ownership.'}
            _status_at = time.monotonic()
        return dict(_status_value)


def change_unit(action):
    if action not in ('start', 'stop'):
        raise ValueError('Unsupported prepared runtime action.')
    result = gpu_lease.systemctl(action, STRATA, timeout=35)
    if result.returncode:
        raise ValueError('Prepared Strata user service could not ' + action + '. Inspect its private journal.')


def start(lab, request):
    if sys.platform != 'linux':
        raise ValueError('Prepared runtime switching is a Linux option.')
    if set(request) != {'target'} or request['target'] not in ('strata', 'fast4b'):
        raise ValueError('Choose only strata or fast4b; service names and commands are fixed.')
    target = request['target']
    with lab.lock:
        lab.guard_runtime()
        if lab.generation.locked() or lab.engine.status()['state'] == 'STARTING':
            raise ValueError('Finish or cancel the current model operation first.')
        if not lab.llama_exe() or 'qwen35-4b' not in lab.settings['models']:
            raise ValueError('The fast 4B recovery runtime must already be prepared.')
        conn = dict(lab.connection or {})
        if conn.get('ownership') == 'OWNED' and conn.get('compute') == 'cpu':
            raise ValueError('Unload the owned CPU engine explicitly before starting a prepared GPU runtime. Its compute lane will not be changed silently.')
        if conn.get('ownership') == 'EXTERNAL' and not (
                conn.get('kind') == 'strata' and conn.get('base') == 'http://127.0.0.1:8880/v1'):
            raise ValueError('Disconnect the unrelated external backend first. It will not be stopped.')
        pid = lab.engine.status().get('pid') if lab.engine.proc is not None else None
        lease = gpu_lease.acquire(pid, allow_strata=True)
        try:
            job = lab.new_job('runtime-switch')
            lab.runtime_job = job.id
            job.update(target=target, message='Preparing ' + target + '\u2026')
        except Exception:
            lease.close()
            raise
    threading.Thread(target=worker, args=(lab, job, target, lease, bool(conn.get('ownership') == 'OWNED')),
                     daemon=True).start()
    return job.id


def wait_fast(lab, job, *, restoring=False):
    if gpu_lease.compute_pids():
        raise ValueError('A GPU process remains; fast 4B was not started.')
    child = lab.jobs[lab.start_llama('qwen35-4b', 'balanced', _switch_job=job.id)]
    deadline = time.monotonic() + 190
    job.update(child_job_id=child.id, message='Restoring fast 4B\u2026' if restoring else 'Loading fast 4B\u2026')
    while child.snapshot()['state'] == 'RUNNING':
        if (job.cancelled.is_set() and not restoring) or time.monotonic() > deadline:
            child.cancel()
            lab.stop_engine(_switch_job=job.id)
            raise InterruptedError('Fast runtime load cancelled.')
        time.sleep(.25)
    if child.snapshot()['state'] != 'COMPLETED':
        raise ValueError('Fast 4B did not become ready. Inspect its engine log.')


def worker(lab, job, target, lease, had_fast):
    started_here = False
    unloaded_fast = False
    began = time.monotonic()
    final = 'FAILED'
    try:
        if job.cancelled.is_set():
            raise InterruptedError('Switch cancelled before changing runtime.')
        if target == 'strata':
            if lab.engine.proc is not None:
                lab.stop_engine(_switch_job=job.id)
                unloaded_fast = True
            if lab.connection:
                lab.disconnect(_switch_job=job.id)
            if job.cancelled.is_set():
                raise InterruptedError('Switch cancelled.')
            if gpu_lease.unit_state(STRATA) in ('inactive', 'failed'):
                if gpu_lease.compute_pids():
                    raise ValueError('GPU ownership changed before Strata start; nothing was started.')
                change_unit('start')
                started_here = True
            deadline = time.monotonic() + 1200
            while time.monotonic() < deadline:
                if job.cancelled.is_set():
                    raise InterruptedError('Strata startup cancelled.')
                if gpu_lease.unit_state(STRATA) in ('inactive', 'failed'):
                    raise ValueError('Prepared Strata exited during startup.')
                job.update(elapsed_seconds=round(time.monotonic() - began),
                           message='Loading prepared Strata. Cold startup previously took about 15 minutes; no download is running.')
                try:
                    lab.connect_haven_strata(_switch_job=job.id)
                    if job.cancelled.is_set():
                        raise InterruptedError('Strata startup cancelled at readiness.')
                    final = 'COMPLETED'
                    job.update(message='Strata is ready. Chat here in Haven.', progress=1)
                    break
                except (OSError, http.client.HTTPException):
                    pass
                except ValueError as error:
                    if not any(s in str(error) for s in ('HTTP 503', 'No model was reported', 'credential is unavailable')):
                        raise
                if job.cancelled.wait(5):
                    raise InterruptedError('Strata startup cancelled.')
            else:
                raise TimeoutError('Strata was not ready within the 20-minute startup bound.')
        else:
            # This is an explicit operation on one named Haven unit. Generic
            # disconnect/unload still never kills an external backend.
            if gpu_lease.unit_state(STRATA) not in ('inactive', 'failed'):
                job.update(message='Stopping the prepared Haven Strata service\u2026')
                change_unit('stop')
                if gpu_lease.unit_state(STRATA) not in ('inactive', 'failed'):
                    raise ValueError('Strata stop was not confirmed; fast 4B was not started.')
            if lab.connection and lab.connection.get('ownership') == 'EXTERNAL':
                lab.disconnect(_switch_job=job.id)
            elif lab.connection and (lab.connection.get('model_sha256') != lab.settings['models']['qwen35-4b'].get('sha256')
                                     or lab.engine.status()['state'] != 'READY'):
                lab.stop_engine(_switch_job=job.id)
            if lab.engine.proc is None:
                wait_fast(lab, job)
            job.update(message='Fast 4B is ready. Chat here in Haven.', progress=1)
            final = 'COMPLETED'
    except Exception as error:
        final = 'CANCELLED' if job.cancelled.is_set() else 'FAILED'
        job.update(error=str(error)[:400])
        if started_here:
            try:
                change_unit('stop')
                job.update(strata_cleanup=gpu_lease.unit_state(STRATA))
            except Exception:
                job.update(cleanup_error='Prepared Strata stop was not confirmed.')
        if had_fast and unloaded_fast and not lab.shutting_down:
            try:
                if gpu_lease.unit_state(STRATA) in ('inactive', 'failed') and not gpu_lease.compute_pids():
                    wait_fast(lab, job, restoring=True)
                    job.update(fast4b_restored=True)
            except Exception:
                job.update(recovery_error='Fast 4B recovery failed; use its existing load control.')
    finally:
        lease.close()
        with lab.lock:
            lab.runtime_job = None
            job.update(state=final, completed_at=time.time(), elapsed_seconds=round(time.monotonic() - began, 2))
