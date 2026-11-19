import fcntl
import json
import os
import pathlib
import signal
import socket
import stat
import struct
import subprocess
import sys
import time


LIMIT = 16384
SERVICE = "org.freedesktop.secrets"
ROOT = "/org/freedesktop/secrets"
INTERNAL = "org.gnome.keyring.InternalUnsupportedGuiltRiddenInterface"


def runtime_directory():
    root = pathlib.Path(os.environ.get("XDG_DATA_HOME", "/config/.local/share"))
    directory = root / "dev-workspace-desktop" / "keyring-control"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("Keyring control directory ownership is invalid.")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Keyring control directory must be private.")
    return directory


def receive(connection):
    value = bytearray()
    while len(value) <= LIMIT:
        part = connection.recv(min(4096, LIMIT + 1 - len(value)))
        if not part:
            break
        value.extend(part)
        if b"\n" in part:
            break
    if len(value) > LIMIT or not value.endswith(b"\n"):
        raise ValueError("Invalid keyring request size or framing.")
    result = json.loads(value)
    if not isinstance(result, dict):
        raise ValueError("Invalid keyring request.")
    return result


def request(payload):
    destination = runtime_directory() / "control.sock"
    info = destination.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("Invalid keyring control socket.")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError("Keyring control socket must be private.")
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(60)
        connection.connect(str(destination))
        peer = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if peer[1] != os.getuid():
            raise ValueError("Keyring service ownership is invalid.")
        connection.sendall(json.dumps(payload).encode() + b"\n")
        result = receive(connection)
    if not result.get("ok"):
        raise ValueError(result.get("error", "Keyring operation failed."))
    return result["value"]


class Keyring:
    def __init__(self):
        from gi.repository import Gio, GLib

        self.GLib = GLib
        self.Gio = Gio
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.call(ROOT, "org.freedesktop.Secret.Service", "ReadAlias", "(s)", ("default",))
        self.session = self.call(ROOT, "org.freedesktop.Secret.Service", "OpenSession", "(sv)", ("plain", GLib.Variant("s", "")))[1]

    def call(self, path, interface, method, signature, values):
        return self.bus.call_sync(SERVICE, path, interface, method, self.GLib.Variant(signature, values), None, self.Gio.DBusCallFlags.NONE, 10000, None).unpack()

    def collection(self):
        return self.call(ROOT, "org.freedesktop.Secret.Service", "ReadAlias", "(s)", ("default",))[0]

    def status(self):
        collection = self.collection()
        if collection == "/":
            return {"state": "not-created"}
        locked = self.call(collection, "org.freedesktop.DBus.Properties", "Get", "(ss)", ("org.freedesktop.Secret.Collection", "Locked"))[0]
        return {"state": "locked" if locked else "unlocked"}

    def secret(self, value):
        return (self.session, [], list(value.encode("utf-8")), "text/plain; charset=utf8")

    def password(self, payload, name):
        value = payload.get(name)
        if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 1024 or "\0" in value:
            raise ValueError("Enter a nonempty keyring password of at most 1024 bytes.")
        return value

    def perform(self, payload):
        operation = payload.get("operation")
        allowed = {"status": {"operation"}, "environment": {"operation"}, "unlock": {"operation", "password"}, "set": {"operation", "currentPassword", "password", "confirmation"}}
        if operation not in allowed or not set(payload).issubset(allowed[operation]):
            raise ValueError("Invalid keyring operation or fields.")
        if operation == "status":
            return self.status()
        if operation == "environment":
            return {**self.status(), "address": os.environ["DBUS_SESSION_BUS_ADDRESS"]}
        password = self.password(payload, "password")
        collection = self.collection()
        if operation == "set":
            if password != payload.get("confirmation"):
                raise ValueError("The new keyring passwords do not match.")
            if len(password) < 12:
                raise ValueError("Choose a keyring password of at least 12 characters.")
            if collection == "/":
                if payload.get("currentPassword"):
                    raise ValueError("No default keyring exists. Leave the current password empty.")
                properties = {"org.freedesktop.Secret.Collection.Label": self.GLib.Variant("s", "Desktop Keyring")}
                collection = self.call(ROOT, INTERNAL, "CreateWithMasterPassword", "(a{sv}(oayays))", (properties, self.secret(password)))[0]
                self.call(ROOT, "org.freedesktop.Secret.Service", "SetAlias", "(so)", ("default", collection))
            else:
                current = self.password(payload, "currentPassword")
                self.call(ROOT, INTERNAL, "ChangeWithMasterPassword", "(o(oayays)(oayays))", (collection, self.secret(current), self.secret(password)))
        elif collection == "/":
            raise ValueError("Create the keyring using Set Keyring Password first.")
        self.call(ROOT, INTERNAL, "UnlockWithMasterPassword", "(o(oayays))", (collection, self.secret(password)))
        state = self.status()
        if state["state"] != "unlocked":
            raise ValueError("The keyring could not be unlocked.")
        return state


def serve():
    os.umask(0o077)
    directory = runtime_directory()
    descriptor = os.open(directory / "service.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return
    destination = directory / "control.sock"
    if destination.exists() or destination.is_symlink():
        info = destination.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Refusing to replace an invalid keyring socket.")
        destination.unlink()
    environment = dict(os.environ)
    environment.pop("GNOME_KEYRING_CONTROL", None)
    daemon = subprocess.Popen(["gnome-keyring-daemon", "--foreground", "--components=secrets", "--control-directory=" + str(directory)], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    stopping = False
    def stop(signum, frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                keyring = Keyring()
                break
            except Exception:
                if daemon.poll() is not None or time.monotonic() >= deadline:
                    raise ValueError("The private keyring service did not start.") from None
                time.sleep(0.1)
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(str(destination))
            destination.chmod(0o600)
            server.listen(8)
            server.settimeout(1)
            published = None
            while daemon.poll() is None and not stopping:
                current = keyring.status()
                if current != published:
                    temporary = directory / "status.pending"
                    with open(temporary, "w", opener=lambda path, flags: os.open(path, flags | os.O_NOFOLLOW, 0o600)) as output:
                        json.dump(current, output)
                        output.write("\n")
                    os.replace(temporary, directory / "status.json")
                    published = current
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    continue
                with connection:
                    connection.settimeout(5)
                    try:
                        peer = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                        if peer[1] != os.getuid():
                            raise ValueError("Keyring client ownership is invalid.")
                        value = keyring.perform(receive(connection))
                        response = {"ok": True, "value": value}
                    except ValueError as error:
                        response = {"ok": False, "error": str(error)}
                    except Exception:
                        response = {"ok": False, "error": "Keyring operation was rejected. Check the current password and try again; saved credentials are retained."}
                    try:
                        connection.sendall(json.dumps(response).encode() + b"\n")
                    except OSError:
                        pass
    finally:
        try:
            if daemon.poll() is None:
                daemon.terminate()
                try:
                    daemon.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    daemon.kill()
                    daemon.wait(timeout=5)
        finally:
            if destination.exists():
                destination.unlink()
            (directory / "status.json").unlink(missing_ok=True)
            os.close(descriptor)


def main():
    os.umask(0o077)
    mode = sys.argv[1] if len(sys.argv) > 1 else "request"
    if mode == "serve":
        serve()
    elif mode == "supervise":
        directory = runtime_directory()
        os.environ.setdefault("XDG_RUNTIME_DIR", str(directory))
        os.execvp("dbus-run-session", ["dbus-run-session", "--", sys.executable, "-B", __file__, "serve"])
    elif mode == "request":
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("Keyring request is too large.")
        print(json.dumps(request(json.loads(raw))))
    elif mode == "editor":
        while True:
            try:
                value = request({"operation": "environment"})
                if value["state"] == "unlocked":
                    break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = value["address"]
        editor = "/config/.local/share/dev-workspace-desktop/editor/current/bin/code"
        os.execv(editor, [editor, "--ozone-platform=wayland", "--password-store=gnome-libsecret", *sys.argv[2:]])
    else:
        raise ValueError("Unknown keyring command.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Keyring access failed. Verify the desktop is running and check the keyring password. Saved credentials were not reset.", file=sys.stderr)
        sys.exit(1)
