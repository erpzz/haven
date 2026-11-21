"""Explicit operator-only setup of an isolated localhost sample installation."""
import argparse
import fcntl
import getpass
import json
import os
import secrets
import subprocess
import time

from .local import request
from .samples import FILES, ROOT, checked, read, save


def verify_deployment():
    """Only bootstrap the loopback port owned by this pinned Compose project."""
    cmd = ["docker", "--host=unix:///var/run/docker.sock", "inspect", "purple-apm-bloodhound-1"]
    container = json.loads(subprocess.check_output(cmd))[0]
    config = container["Config"]
    ports = container["NetworkSettings"]["Ports"].get("8080/tcp")
    if (not container["State"]["Running"] or config["Labels"]["com.docker.compose.project"] != "purple-apm"
            or config["Labels"]["com.docker.compose.service"] != "bloodhound"
            or not config["Image"].endswith("@sha256:75c3b4c2c9213981d13e36520db4a2d66a9a290abd9ad93db29dd3564a70deac")
            or ports != [{"HostIp": "127.0.0.1", "HostPort": "8080"}]):
        raise PermissionError("Expected the dedicated pinned sample deployment")


def setup(action, password):
    def api(method, path, payload=None):
        return request(8080, method, "/api/v2/" + path,
                       json.dumps(payload) if payload is not None else None, headers)

    verify_deployment()
    headers = {"Content-Type": "application/json"}
    login = api("POST", "login", {"username": "admin", "login_method": "secret", "secret": password})
    headers["Authorization"] = "Bearer " + login["data"]["session_token"]
    if action == "reader":
        if (ROOT / "reader.json").exists():
            raise ValueError("Reader credentials already exist")
        roles = api("GET", "roles")["data"]["roles"]
        role = next(r for r in roles if r["name"] == "Read-Only")
        principal = "purple-sample-reader"
        users = api("GET", "bloodhound-users")["data"]["users"]
        user = next((u for u in users if u["principal_name"] == principal), None)
        if user is None:
            result = api("POST", "bloodhound-users", {"principal": principal, "roles": [role["id"]],
                         "secret": secrets.token_urlsafe(36), "needs_password_reset": False})
            user = result["data"]
        if [r["name"] for r in user["roles"]] != ["Read-Only"]:
            raise ValueError("Reader role mismatch")
        token = api("POST", "tokens", {"user_id": user["id"], "token_name": "purple-sample"})["data"]
        save("reader.json", {"id": token["id"], "key": token["key"]})
        return

    archives = {name: checked(name) for name in FILES}
    if (ROOT / "ingest.json").exists():
        record = read("ingest.json")
        if record["phase"] == "uploading":
            # A crash may have interrupted a ZIP POST or the request to end the job.
            # CE can report a terminal/processing job; never end an uncertain upload.
            jobs = api("GET", f"file-upload?id=eq:{record['job']}")["data"]
            found = next(j for j in jobs if j["id"] == record["job"])
            if found["status"] in (0, 1):
                save(f"interrupted-job-{record['job']}.json", record)
                record = None
    else:
        record = None
    if record is None:
        job = api("POST", "file-upload/start")["data"]["id"]
        record = {"job": job, "archives": FILES, "phase": "uploading"}
        save("ingest.json", record)
        for name, data in archives.items():
            request(8080, "POST", f"/api/v2/file-upload/{job}", data, {
                **headers, "Content-Type": "application/zip", "X-File-Upload-Name": name})
        api("POST", f"file-upload/{job}/end")
        record["phase"] = "waiting"
        save("ingest.json", record)
    job = record["job"]
    for _ in range(240):
        rows = api("GET", f"file-upload?id=eq:{job}")["data"]
        status = next(j for j in rows if j["id"] == job)
        if status["status"] in (2, 3, 4, 5, 8, -1):
            record.update(status=status, phase="terminal")
            save("ingest.json", record)
            if (status["status"] != 2 or status["failed_files"] or status["partial_failed_files"]
                    or status["total_files"] != 32):
                raise RuntimeError(f"Incomplete sample ingest job {job}")
            print("Completed sample upload job", job)
            return
        time.sleep(3)
    raise TimeoutError(f"Inspect sample ingest job {job} before retry")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["reader", "ingest"])
    action = parser.parse_args().action
    ROOT.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (ROOT / f"{action}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        setup(action, os.getenv("APM_SETUP_PASSWORD") or getpass.getpass("Local CE admin password: "))
