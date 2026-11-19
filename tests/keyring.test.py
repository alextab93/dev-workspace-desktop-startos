import importlib.util
import os
import pathlib
import signal
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "assets" / "keyring.py"
spec = importlib.util.spec_from_file_location("desktop_keyring", SOURCE)
keyring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keyring)


@unittest.skipUnless(sys.platform == "linux", "Requires a Linux Secret Service and D-Bus")
class KeyringTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="desktop-keyring-test-")
        self.directory = pathlib.Path(self.temporary.name)
        self.previous = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = str(self.directory / "data")
        self.environment = dict(os.environ)
        self.environment["XDG_RUNTIME_DIR"] = str(self.directory / "runtime")
        pathlib.Path(self.environment["XDG_RUNTIME_DIR"]).mkdir(mode=0o700)
        self.environment.pop("GNOME_KEYRING_CONTROL", None)
        self.environment.pop("DBUS_SESSION_BUS_ADDRESS", None)
        self.process = None
        self.service = None
        self.connection = None
        self.password = "disposable-old-keyring-password"
        self.replacement = "disposable-new-keyring-password"
        self.addCleanup(self.cleanup)
        self.start()

    def cleanup(self):
        try:
            self.stop()
        finally:
            if self.previous is None:
                os.environ.pop("XDG_DATA_HOME", None)
            else:
                os.environ["XDG_DATA_HOME"] = self.previous
            self.temporary.cleanup()

    def start(self):
        self.log = tempfile.TemporaryFile()
        self.process = subprocess.Popen([sys.executable, "-B", str(SOURCE), "supervise"], env=self.environment, start_new_session=True, stdout=subprocess.DEVNULL, stderr=self.log)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                keyring.request({"operation": "status"})
                with socket.socket(socket.AF_UNIX) as connection:
                    connection.connect(str(keyring.runtime_directory() / "control.sock"))
                    peer = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    self.assertEqual(peer[1], os.getuid())
                    self.service = os.pidfd_open(peer[0])
                return
            except (OSError, ValueError):
                if self.process.poll() is not None:
                    self.log.seek(0)
                    self.fail("Isolated keyring exited before readiness: " + self.log.read().decode())
                time.sleep(0.1)
        self.fail("Isolated keyring did not become ready")

    def stop(self):
        if self.connection is not None:
            self.connection.close_sync(None)
            self.connection = None
        if self.process is not None:
            if self.process.poll() is None:
                if self.service is not None:
                    signal.pidfd_send_signal(self.service, signal.SIGTERM)
                else:
                    os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
                raise
            if self.service is not None:
                os.close(self.service)
                self.service = None
            deadline = time.monotonic() + 5
            while (keyring.runtime_directory() / "control.sock").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.log.seek(0)
            self.assertFalse((keyring.runtime_directory() / "control.sock").exists(), self.log.read().decode())
            self.log.close()
            self.process = None

    def create(self):
        return keyring.request({"operation": "set", "password": self.password, "confirmation": self.password})

    def bus(self):
        from gi.repository import Gio

        if self.connection is None:
            value = keyring.request({"operation": "environment"})
            self.connection = Gio.DBusConnection.new_for_address_sync(value["address"], Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION, None, None)
        return self.connection

    def call(self, path, interface, method, signature, values):
        from gi.repository import Gio, GLib

        return self.bus().call_sync(keyring.SERVICE, path, interface, method, GLib.Variant(signature, values), None, Gio.DBusCallFlags.NONE, 10000, None).unpack()

    def collection(self):
        return self.call(keyring.ROOT, "org.freedesktop.Secret.Service", "ReadAlias", "(s)", ("default",))[0]

    def lock(self):
        self.call(keyring.ROOT, "org.freedesktop.Secret.Service", "Lock", "(ao)", ([self.collection()],))
        self.assertEqual(keyring.request({"operation": "status"}), {"state": "locked"})

    def test_create_unlock_rotate_restart_preserves_exact_saved_credential(self):
        from gi.repository import GLib

        self.assertEqual(keyring.request({"operation": "status"}), {"state": "not-created"})
        self.assertEqual(self.create(), {"state": "unlocked"})
        session = self.call(keyring.ROOT, "org.freedesktop.Secret.Service", "OpenSession", "(sv)", ("plain", GLib.Variant("s", "")))[1]
        value = b"owned-disposable-secret-exact-bytes"
        attributes = {"org.freedesktop.Secret.Item.Label": GLib.Variant("s", "Owned fixture"), "org.freedesktop.Secret.Item.Attributes": GLib.Variant("a{ss}", {"fixture": "keyring-action"})}
        item, prompt = self.call(self.collection(), "org.freedesktop.Secret.Collection", "CreateItem", "(a{sv}(oayays)b)", (attributes, (session, [], list(value), "text/plain"), False))
        self.assertEqual(prompt, "/")
        with self.assertRaises(ValueError):
            keyring.request({"operation": "set", "currentPassword": "incorrect-password", "password": self.replacement, "confirmation": self.replacement})
        self.lock()
        with self.assertRaises(ValueError):
            keyring.request({"operation": "unlock", "password": "incorrect-password"})
        self.assertEqual(keyring.request({"operation": "status"}), {"state": "locked"})
        self.assertEqual(keyring.request({"operation": "unlock", "password": self.password}), {"state": "unlocked"})
        self.assertEqual(keyring.request({"operation": "set", "currentPassword": self.password, "password": self.replacement, "confirmation": self.replacement}), {"state": "unlocked"})
        self.lock()
        with self.assertRaises(ValueError):
            keyring.request({"operation": "unlock", "password": self.password})
        self.assertEqual(keyring.request({"operation": "unlock", "password": self.replacement}), {"state": "unlocked"})
        secret = self.call(item, "org.freedesktop.Secret.Item", "GetSecret", "(o)", (session,))[0]
        self.assertEqual(bytes(secret[2]), value)
        self.stop()
        self.start()
        self.assertEqual(keyring.request({"operation": "status"}), {"state": "locked"})
        self.assertEqual(keyring.request({"operation": "unlock", "password": self.replacement}), {"state": "unlocked"})
        session = self.call(keyring.ROOT, "org.freedesktop.Secret.Service", "OpenSession", "(sv)", ("plain", GLib.Variant("s", "")))[1]
        items = self.call(self.collection(), "org.freedesktop.Secret.Collection", "SearchItems", "(a{ss})", ({"fixture": "keyring-action"},))[0]
        self.assertEqual(len(items), 1)
        secret = self.call(items[0], "org.freedesktop.Secret.Item", "GetSecret", "(o)", (session,))[0]
        self.assertEqual(bytes(secret[2]), value)
        for path in (self.directory / "data" / "keyrings").glob("*"):
            if path.is_file():
                self.assertNotIn(value, path.read_bytes())
                self.assertNotIn(self.replacement.encode(), path.read_bytes())

    def test_invalid_requests_leave_keyring_uncreated(self):
        for payload in [
            {"operation": "unlock", "password": self.password},
            {"operation": "set", "password": self.password, "confirmation": "different"},
            {"operation": "set", "password": "short", "confirmation": "short"},
            {"operation": "set", "password": self.password, "confirmation": self.password, "currentPassword": "not-empty"},
            {"operation": "delete"},
            {"operation": "set", "password": self.password, "confirmation": self.password, "reset": True},
        ]:
            with self.assertRaises(ValueError):
                keyring.request(payload)
            self.assertEqual(keyring.request({"operation": "status"}), {"state": "not-created"})

    def test_client_errors_do_not_echo_passwords(self):
        self.create()
        self.lock()
        wrong = "private-invalid-password-for-error-test"
        result = subprocess.run([sys.executable, "-B", str(SOURCE), "request"], env=self.environment, input=__import__("json").dumps({"operation": "unlock", "password": wrong}), text=True, capture_output=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(wrong, result.stdout + result.stderr)
        self.assertNotIn(self.password, result.stdout + result.stderr)
        self.assertEqual(keyring.request({"operation": "status"}), {"state": "locked"})

    def test_readable_control_socket_is_rejected_without_changing_keyring(self):
        self.create()
        path = keyring.runtime_directory() / "control.sock"
        path.chmod(0o666)
        try:
            with self.assertRaises(ValueError):
                keyring.request({"operation": "set", "currentPassword": self.password, "password": self.replacement, "confirmation": self.replacement})
        finally:
            path.chmod(0o600)
        self.lock()
        self.assertEqual(keyring.request({"operation": "unlock", "password": self.password}), {"state": "unlocked"})

    def test_status_file_follows_creation_unlock_and_restart(self):
        import json

        path = keyring.runtime_directory() / "status.json"
        def wait(expected):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    if json.loads(path.read_text()) == {"state": expected}:
                        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                        return
                except FileNotFoundError:
                    pass
                time.sleep(0.05)
            self.fail("Published keyring state did not become " + expected)
        wait("not-created")
        self.create()
        wait("unlocked")
        self.lock()
        wait("locked")
        keyring.request({"operation": "unlock", "password": self.password})
        wait("unlocked")
        self.stop()
        self.assertFalse(path.exists())
        self.start()
        wait("locked")

    def test_duplicate_supervisor_preserves_current_session(self):
        self.create()
        before = keyring.request({"operation": "environment"})
        result = subprocess.run([sys.executable, "-B", str(SOURCE), "supervise"], env=self.environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(keyring.request({"operation": "environment"}), before)
        self.lock()
        self.assertEqual(keyring.request({"operation": "unlock", "password": self.password}), {"state": "unlocked"})

    def test_headless_supervisor_creates_its_runtime_without_a_desktop_session(self):
        self.stop()
        for name in ['DISPLAY', 'XAUTHORITY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR']:
            self.environment.pop(name, None)
        self.start()
        self.assertEqual(keyring.request({"operation": "status"}), {"state": "not-created"})
        self.assertEqual(self.create(), {"state": "unlocked"})
        self.lock()
        self.assertEqual(keyring.request({"operation": "unlock", "password": self.password}), {"state": "unlocked"})

    @unittest.skipUnless(os.environ.get("DESKTOP_TEST_EXISTING_KEYRINGS"), "No encrypted migration fixture supplied")
    def test_existing_encrypted_keyring_is_detected_without_decryption(self):
        import hashlib

        self.stop()
        source = pathlib.Path(os.environ["DESKTOP_TEST_EXISTING_KEYRINGS"])
        target = pathlib.Path(os.environ["XDG_DATA_HOME"]) / "keyrings"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        def snapshot():
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file()}
        before = snapshot()
        self.start()
        self.assertEqual(keyring.request({"operation": "status"}), {"state": "locked"})
        self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
