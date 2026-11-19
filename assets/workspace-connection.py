#!/usr/bin/env python3
import argparse
import base64
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import uuid


ALIAS = "dev-workspace"
HOST_ALIAS = "dev-workspace-pinned"
FOLDERS = ("/home/dev/projects", "/projects-shared")


def atomic_write(destination, content):
    if destination.is_symlink():
        raise ValueError("A managed connection file cannot be a symbolic link.")
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
        directory = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def parse_endpoint(value):
    parsed = urllib.parse.urlsplit("ssh://" + value)
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("Invalid workspace SSH address.")
    host = str(ipaddress.ip_address(parsed.hostname or ""))
    port = parsed.port
    if port is None or not 1 <= port <= 65535:
        raise ValueError("Invalid workspace SSH port.")
    return {"host": host, "port": port}


def public_identity(value):
    parts = value.strip().split()
    if len(parts) < 2 or parts[0] != "ssh-ed25519":
        raise ValueError("An Ed25519 public key is required.")
    blob = base64.b64decode(parts[1], validate=True)
    if len(blob) != 51 or blob[:19] != b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20":
        raise ValueError("Invalid Ed25519 public key.")
    public_key = "ssh-ed25519 " + base64.b64encode(blob).decode()
    fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
    return public_key, fingerprint


def run(arguments, timeout=15):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise ValueError("The workspace SSH operation failed: " + (result.stderr.strip() or "connection unavailable"))
    return result.stdout


class WorkspaceConnection:
    def __init__(self, home):
        self.home = Path(home)
        self.ssh = self.home / ".ssh"
        self.root = self.ssh / "dev-workspace-desktop"
        for directory in (self.home, self.ssh, self.root):
            if directory.is_symlink():
                raise ValueError("Connection directories cannot be symbolic links.")
            directory.mkdir(exist_ok=True, mode=0o700)
        self.keys = self.root / "keys"
        if self.keys.is_symlink():
            raise ValueError("The key directory cannot be a symbolic link.")
        self.keys.mkdir(exist_ok=True, mode=0o700)
        self.identity = self.root / "identity"
        self.configuration = self.root / "config"
        self.state_file = self.root / "connection.json"
        self.known_hosts = self.root / "known_hosts"
        descriptor = os.open(self.root / "lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        self.lock = os.fdopen(descriptor, "w")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.lock.close()
            raise ValueError("Another workspace connection action is running.") from error

    def close(self):
        self.lock.close()

    def key_directory(self):
        if not self.identity.exists() and not self.identity.is_symlink():
            return None
        if not self.identity.is_symlink():
            raise ValueError("Invalid managed key selection.")
        target = os.readlink(self.identity)
        if not re.fullmatch(r"keys/[a-f0-9]{32}", target):
            raise ValueError("Invalid managed key selection.")
        directory = self.root / target
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("The selected key directory is unavailable.")
        return directory

    def key_info(self):
        directory = self.key_directory()
        if directory is None:
            return None
        private_key = directory / "id_ed25519"
        if private_key.is_symlink() or not private_key.is_file() or private_key.stat().st_mode & 0o077:
            raise ValueError("The workspace private key is missing or has unsafe permissions.")
        derived = run(["ssh-keygen", "-y", "-P", "", "-f", str(private_key)])
        public_key, fingerprint = public_identity(derived)
        return {"publicKey": public_key, "keyFingerprint": fingerprint}

    def include_configuration(self):
        target = self.ssh / "config"
        if target.is_symlink():
            raise ValueError("Manage the existing SSH config symlink before enabling this connection.")
        current = target.read_text() if target.exists() else ""
        escaped = str(self.configuration).replace("\\", "\\\\").replace('"', '\\"')
        if "\n" in escaped or "\r" in escaped:
            raise ValueError("The desktop home path cannot contain line breaks.")
        include = f'Include "{escaped}"\n'
        if not current.startswith(include):
            atomic_write(target, include + current)

    def block_connection(self):
        atomic_write(self.configuration, f"Host {ALIAS}\n  ProxyCommand /bin/false\nHost *\n")

    def prepare_key(self, rotate=False):
        previous = self.key_info()
        self.include_configuration()
        if previous is not None and not rotate:
            return previous
        old_directory = self.key_directory()
        directory = self.keys / uuid.uuid4().hex
        directory.mkdir(mode=0o700)
        try:
            run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "Dev Workspace Desktop", "-f", str(directory / "id_ed25519")])
            self.block_connection()
            atomic_write(self.state_file, "null\n")
            temporary = self.root / (".identity-" + uuid.uuid4().hex)
            try:
                temporary.symlink_to(directory.relative_to(self.root), target_is_directory=True)
                os.replace(temporary, self.identity)
                descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            finally:
                temporary.unlink(missing_ok=True)
        except Exception:
            if not self.identity.is_symlink() or self.identity.resolve() != directory:
                shutil.rmtree(directory)
            raise
        if old_directory is not None:
            for name in ("id_ed25519", "id_ed25519.pub"):
                (old_directory / name).unlink(missing_ok=True)
            old_directory.rmdir()
        result = self.key_info()
        if previous:
            result["previousFingerprint"] = previous["keyFingerprint"]
        return result

    def read_state(self):
        if self.state_file.is_symlink():
            raise ValueError("The connection state cannot be a symbolic link.")
        state = json.loads(self.state_file.read_text()) if self.state_file.exists() else None
        if state is None:
            return None
        if not isinstance(state, dict) or state.get("folder") not in FOLDERS:
            raise ValueError("Invalid workspace connection state.")
        endpoint = state.get("endpoint")
        if endpoint is not None:
            if not isinstance(endpoint, dict) or type(endpoint.get("port")) is not int or not 1 <= endpoint["port"] <= 65535:
                raise ValueError("Invalid retained workspace SSH address.")
            endpoint = {"host": str(ipaddress.ip_address(endpoint.get("host", ""))), "port": endpoint["port"]}
        public_key, fingerprint = public_identity(state.get("hostKey", ""))
        key = self.key_info()
        if key is None or fingerprint != state.get("hostFingerprint") or key["keyFingerprint"] != state.get("keyFingerprint"):
            raise ValueError("The retained workspace identity does not match its connection.")
        return state | {"hostKey": public_key, "endpoint": endpoint}

    def ssh_arguments(self, endpoint, known_hosts):
        return ["ssh", "-F", "/dev/null", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "-o", "ConnectionAttempts=1", "-o", "StrictHostKeyChecking=yes", "-o", "GlobalKnownHostsFile=/dev/null", "-o", f"UserKnownHostsFile={known_hosts}", "-o", f"HostKeyAlias={HOST_ALIAS}", "-o", "IdentitiesOnly=yes", "-o", "IdentityAgent=none", "-o", "ForwardAgent=no", "-o", "ControlMaster=no", "-o", "ControlPath=none", "-i", str(self.identity / "id_ed25519"), "-p", str(endpoint["port"]), "--", "dev@" + endpoint["host"]]

    def verify_connection(self, endpoint, known_hosts, folder):
        if folder not in FOLDERS:
            raise ValueError("Choose a supported project folder.")
        output = run(self.ssh_arguments(endpoint, known_hosts) + [f"test -d {folder} && printf 'dev-workspace-desktop-ready\\n'"])
        if output != "dev-workspace-desktop-ready\n":
            raise ValueError("The workspace did not return the expected connection result.")

    def write_configuration(self, state):
        endpoint = state.get("endpoint")
        if endpoint is None:
            self.block_connection()
            return
        private_key = str(self.identity / "id_ed25519").replace("\\", "\\\\").replace('"', '\\"')
        known_hosts = str(self.known_hosts).replace("\\", "\\\\").replace('"', '\\"')
        atomic_write(self.known_hosts, f"{HOST_ALIAS} {state['hostKey']}\n")
        atomic_write(self.configuration, f'Host {ALIAS}\n  HostName {endpoint["host"]}\n  Port {endpoint["port"]}\n  User dev\n  IdentityFile "{private_key}"\n  IdentitiesOnly yes\n  IdentityAgent none\n  ForwardAgent no\n  StrictHostKeyChecking yes\n  HostKeyAlias {HOST_ALIAS}\n  UserKnownHostsFile "{known_hosts}"\n  GlobalKnownHostsFile /dev/null\n  ControlMaster no\n  ControlPath none\n  ServerAliveInterval 30\n  ServerAliveCountMax 3\nHost *\n')

    def pair(self, address, fingerprint, folder):
        key = self.key_info()
        if key is None:
            raise ValueError("Prepare and authorize the workspace key first.")
        if not re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", fingerprint):
            raise ValueError("Copy the SHA256 host fingerprint from Dev Workspace Connection Information.")
        if folder not in FOLDERS:
            raise ValueError("Choose a supported project folder.")
        endpoint = parse_endpoint(address)
        scan = run(["ssh-keyscan", "-T", "5", "-p", str(endpoint["port"]), "-t", "ed25519", endpoint["host"]])
        keys = set()
        for line in scan.splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) >= 3:
                keys.add(public_identity(" ".join(fields[1:3]))[0])
        matches = [key for key in keys if public_identity(key)[1] == fingerprint]
        if len(matches) != 1:
            raise ValueError("The workspace host fingerprint does not match. Keep the existing connection unchanged.")
        descriptor, candidate = tempfile.mkstemp(prefix=".known-hosts-", dir=self.root)
        try:
            with os.fdopen(descriptor, "w") as output:
                output.write(f"{HOST_ALIAS} {matches[0]}\n")
            self.verify_connection(endpoint, candidate, folder)
        finally:
            Path(candidate).unlink(missing_ok=True)
        state = {"hostKey": matches[0], "hostFingerprint": fingerprint, "keyFingerprint": key["keyFingerprint"], "folder": folder, "endpoint": endpoint}
        self.block_connection()
        atomic_write(self.state_file, json.dumps(state, sort_keys=True) + "\n")
        self.write_configuration(state)
        self.include_configuration()
        return self.status()

    def refresh(self, address):
        try:
            state = self.read_state()
            endpoint = parse_endpoint(address) if address else None
        except (ValueError, OSError, TypeError):
            self.block_connection()
            raise
        if state is None:
            self.block_connection()
            return self.status()
        state["endpoint"] = endpoint
        self.block_connection()
        atomic_write(self.state_file, json.dumps(state, sort_keys=True) + "\n")
        self.write_configuration(state)
        self.include_configuration()
        return self.status()

    def forget(self):
        self.block_connection()
        atomic_write(self.state_file, "null\n")
        self.known_hosts.unlink(missing_ok=True)
        return self.status()

    def status(self):
        key = self.key_info()
        state = self.read_state()
        result = {"state": "unpaired", "alias": ALIAS, **(key or {})}
        if state is not None:
            result.update({"state": "paired" if state.get("endpoint") else "offline", "folder": state["folder"], "hostFingerprint": state["hostFingerprint"], "endpoint": state.get("endpoint")})
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("key", "rotate", "pair", "refresh", "forget", "status", "check"))
    parser.add_argument("--home", default="/config")
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--fingerprint", default="")
    parser.add_argument("--folder", choices=FOLDERS, default=FOLDERS[0])
    options = parser.parse_args()
    connection = None
    try:
        connection = WorkspaceConnection(options.home)
        if options.command in ("key", "rotate"):
            result = connection.prepare_key(options.command == "rotate")
        elif options.command == "pair":
            result = connection.pair(options.endpoint, options.fingerprint.strip(), options.folder)
        elif options.command == "refresh":
            result = connection.refresh(options.endpoint)
        elif options.command == "forget":
            result = connection.forget()
        elif options.command == "check":
            state = connection.read_state()
            if not state or not state.get("endpoint"):
                raise ValueError("Dev Workspace is not connected or its SSH address is unavailable.")
            connection.verify_connection(state["endpoint"], connection.known_hosts, state["folder"])
            result = connection.status() | {"verified": True}
        else:
            result = connection.status()
        print(json.dumps(result))
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "failed", "message": str(error)}), file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
