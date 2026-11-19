import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid


sys.dont_write_bytecode = True
HELPER = Path(__file__).parents[1] / "assets/workspace-connection.py"
spec = importlib.util.spec_from_file_location("connection_helper", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def execute(*arguments, input=None):
    return subprocess.run(arguments, input=input, capture_output=True, text=True, timeout=30, check=True).stdout.strip()


class WorkspaceFixture:
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.connection = helper.WorkspaceConnection(self.home)
        self.addCleanup(self.connection.close)

    def effective_config(self):
        output = execute("ssh", "-G", "-F", str(self.home / ".ssh/config"), "dev-workspace")
        return dict(line.split(" ", 1) for line in output.splitlines())


class WorkspaceKeyBehavior(WorkspaceFixture, unittest.TestCase):
    def test_key_creation_is_private_persistent_and_matches_openssh_fingerprint(self):
        public = self.connection.prepare_key()
        key = self.connection.identity / "id_ed25519"
        fingerprint = execute("ssh-keygen", "-lf", str(key)).split()[1]
        self.assertEqual(public["keyFingerprint"], fingerprint)
        self.assertEqual(public["publicKey"].split(), execute("ssh-keygen", "-y", "-f", str(key)).split()[:2])
        self.assertEqual(key.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.connection.prepare_key(), public)
        self.assertEqual(self.connection.status()["state"], "unpaired")
        self.assertEqual(self.effective_config()["proxycommand"], "/bin/false")

    def test_existing_ssh_configuration_remains_usable(self):
        config = self.home / ".ssh/config"
        original = "Host my-existing-project\n  HostName 192.0.2.8\n  User another-user\n"
        config.write_text(original)
        self.connection.prepare_key()
        self.assertTrue(config.read_text().endswith(original))
        parsed = dict(line.split(" ", 1) for line in execute("ssh", "-G", "-F", str(config), "my-existing-project").splitlines())
        self.assertEqual(parsed["hostname"], "192.0.2.8")
        self.assertEqual(parsed["user"], "another-user")

    def test_rotation_returns_the_revocable_old_fingerprint_and_replaces_private_key(self):
        old = self.connection.prepare_key()
        previous = self.connection.key_directory()
        current = self.connection.prepare_key(rotate=True)
        self.assertEqual(current["previousFingerprint"], old["keyFingerprint"])
        self.assertNotEqual(current["keyFingerprint"], old["keyFingerprint"])
        self.assertFalse(previous.exists())
        self.assertEqual(self.connection.status()["state"], "unpaired")
        self.assertEqual(self.effective_config()["proxycommand"], "/bin/false")

    def test_invalid_permissions_are_reported_without_rotating_identity(self):
        self.connection.prepare_key()
        key = self.connection.identity / "id_ed25519"
        original = key.read_bytes()
        key.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "unsafe permissions"):
            self.connection.prepare_key()
        self.assertEqual(key.read_bytes(), original)

    def test_lock_contention_reports_an_actionable_failure(self):
        result = subprocess.run(["python3", str(HELPER), "key", "--home", str(self.home)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Another workspace connection action is running", json.loads(result.stderr)["message"])

    def test_unsafe_address_and_folder_do_not_change_identity(self):
        public = self.connection.prepare_key()
        for address in ("localhost:22", "127.0.0.1", "127.0.0.1:0", "name@127.0.0.1:22", "127.0.0.1:22/path", "127.0.0.1:22\nProxyCommand touch /tmp/unsafe"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.connection.pair(address, "SHA256:" + "A" * 43, "/home/dev/projects")
        with self.assertRaisesRegex(ValueError, "supported project folder"):
            self.connection.pair("127.0.0.1:2222", "SHA256:" + "A" * 43, "/tmp; touch /tmp/unsafe")
        self.assertEqual(self.connection.prepare_key(), public)

    def test_corrupt_state_closes_the_managed_ssh_target(self):
        self.connection.prepare_key()
        self.connection.state_file.write_text("not json")
        with self.assertRaises(ValueError):
            self.connection.refresh("127.0.0.1:2222")
        self.assertEqual(self.effective_config()["proxycommand"], "/bin/false")

    def test_symlinked_user_config_is_preserved_and_reported(self):
        original = self.home / "personal-config"
        original.write_text("Host existing\n")
        (self.home / ".ssh/config").symlink_to(original)
        with self.assertRaisesRegex(ValueError, "SSH config symlink"):
            self.connection.prepare_key()
        self.assertEqual(original.read_text(), "Host existing\n")
        self.assertEqual(self.connection.status()["state"], "unpaired")
        self.assertNotIn("publicKey", self.connection.status())


@unittest.skipUnless(os.environ.get("WORKSPACE_TEST_IMAGE"), "Set WORKSPACE_TEST_IMAGE for real SSH integration.")
class WorkspacePairingBehavior(WorkspaceFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.name = "scratch-desktop-pairing-" + uuid.uuid4().hex
        self.marker = uuid.uuid4().hex
        self.public = self.connection.prepare_key()
        command = "mkdir -p /run/sshd /home/dev/projects; test -f /tmp/workspace-host || ssh-keygen -q -t ed25519 -N '' -f /tmp/workspace-host; exec /usr/sbin/sshd -D -e -p 2222 -h /tmp/workspace-host -o AuthorizedKeysFile=/tmp/authorized_keys -o StrictModes=no -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o PermitRootLogin=no -o AllowUsers=dev -o UsePAM=no"
        execute("docker", "create", "--name", self.name, "--label", "dev-workspace-fixture=" + self.marker, "--publish", "127.0.0.1::2222", "--entrypoint", "/bin/sh", os.environ["WORKSPACE_TEST_IMAGE"], "-c", command)
        self.addCleanup(self.remove_container)
        execute("docker", "start", self.name)
        execute("docker", "exec", "-i", self.name, "sh", "-c", "cat > /tmp/authorized_keys; chmod 644 /tmp/authorized_keys", input=self.public["publicKey"] + "\n")
        self.endpoint = execute("docker", "port", self.name, "2222/tcp")
        for _ in range(50):
            try:
                self.host_key = execute("docker", "exec", self.name, "cat", "/tmp/workspace-host.pub")
                break
            except subprocess.CalledProcessError:
                time.sleep(0.1)
        self.host_fingerprint = helper.public_identity(self.host_key)[1]

    def remove_container(self):
        inspection = json.loads(execute("docker", "inspect", self.name))[0]
        self.assertEqual(inspection["Config"]["Labels"]["dev-workspace-fixture"], self.marker)
        execute("docker", "rm", "--force", "--volumes", self.name)

    def pair(self):
        return self.connection.pair(self.endpoint, self.host_fingerprint, "/home/dev/projects")

    def test_pairs_with_verified_host_and_openssh_uses_the_managed_target(self):
        state = self.pair()
        self.assertEqual(state["state"], "paired")
        self.assertEqual(state["hostFingerprint"], self.host_fingerprint)
        output = execute("ssh", "-F", str(self.home / ".ssh/config"), "dev-workspace", "printf 'remote-project-ready\\n'")
        self.assertEqual(output, "remote-project-ready")

    def test_wrong_fingerprint_preserves_the_previous_connection(self):
        self.pair()
        state = self.connection.state_file.read_bytes()
        config = self.connection.configuration.read_bytes()
        with self.assertRaisesRegex(ValueError, "fingerprint does not match"):
            self.connection.pair(self.endpoint, "SHA256:" + "A" * 43, "/home/dev/projects")
        self.assertEqual(self.connection.state_file.read_bytes(), state)
        self.assertEqual(self.connection.configuration.read_bytes(), config)

    def test_unregistered_key_cannot_finish_pairing(self):
        execute("docker", "exec", self.name, "truncate", "-s", "0", "/tmp/authorized_keys")
        with self.assertRaisesRegex(ValueError, "SSH operation failed"):
            self.pair()
        self.assertEqual(self.connection.status()["state"], "unpaired")

    def test_revocation_prevents_a_new_connection_without_replacing_local_identity(self):
        self.pair()
        execute("docker", "exec", self.name, "truncate", "-s", "0", "/tmp/authorized_keys")
        state = self.connection.read_state()
        with self.assertRaisesRegex(ValueError, "Permission denied"):
            self.connection.verify_connection(state["endpoint"], self.connection.known_hosts, state["folder"])
        self.assertEqual(self.connection.status()["keyFingerprint"], self.public["keyFingerprint"])

    def test_rotated_key_requires_separate_authorization(self):
        self.pair()
        rotated = self.connection.prepare_key(rotate=True)
        self.assertEqual(rotated["previousFingerprint"], self.public["keyFingerprint"])
        with self.assertRaisesRegex(ValueError, "Permission denied"):
            self.pair()
        execute("docker", "exec", "-i", self.name, "sh", "-c", "cat > /tmp/authorized_keys", input=rotated["publicKey"] + "\n")
        self.assertEqual(self.pair()["keyFingerprint"], rotated["keyFingerprint"])

    def test_missing_shared_folder_cannot_replace_valid_project(self):
        self.pair()
        state = self.connection.state_file.read_bytes()
        with self.assertRaisesRegex(ValueError, "SSH operation failed"):
            self.connection.pair(self.endpoint, self.host_fingerprint, "/projects-shared")
        self.assertEqual(self.connection.state_file.read_bytes(), state)

    def test_absent_address_blocks_connection_and_reappearance_preserves_trust(self):
        self.pair()
        offline = self.connection.refresh("")
        self.assertEqual(offline["state"], "offline")
        self.assertEqual(self.effective_config()["proxycommand"], "/bin/false")
        restored = self.connection.refresh(self.endpoint)
        self.assertEqual(restored["hostFingerprint"], self.host_fingerprint)
        self.assertEqual(execute("ssh", "-F", str(self.home / ".ssh/config"), "dev-workspace", "printf 'restored'"), "restored")

    def test_invalid_discovered_address_blocks_the_target_and_retains_host_trust(self):
        self.pair()
        with self.assertRaises(ValueError):
            self.connection.refresh("untrusted-host:22")
        self.assertEqual(self.effective_config()["proxycommand"], "/bin/false")
        self.assertEqual(self.connection.status()["hostFingerprint"], self.host_fingerprint)

    def test_restart_uses_the_actual_reassigned_port_and_same_host_key(self):
        self.pair()
        execute("docker", "restart", self.name)
        endpoint = execute("docker", "port", self.name, "2222/tcp")
        state = self.connection.refresh(endpoint)
        self.assertEqual(state["endpoint"], helper.parse_endpoint(endpoint))
        self.assertEqual(state["hostFingerprint"], self.host_fingerprint)
        self.assertEqual(execute("ssh", "-F", str(self.home / ".ssh/config"), "dev-workspace", "printf 'after-restart'"), "after-restart")

    def test_changed_host_key_is_rejected_after_restart(self):
        self.pair()
        execute("docker", "exec", self.name, "sh", "-c", "ssh-keygen -q -t ed25519 -N '' -f /tmp/replacement-host; mv /tmp/replacement-host /tmp/workspace-host; mv /tmp/replacement-host.pub /tmp/workspace-host.pub")
        execute("docker", "restart", self.name)
        self.connection.refresh(execute("docker", "port", self.name, "2222/tcp"))
        with self.assertRaisesRegex(ValueError, "HOST IDENTIFICATION HAS CHANGED"):
            state = self.connection.read_state()
            self.connection.verify_connection(state["endpoint"], self.connection.known_hosts, state["folder"])

    def test_forget_disables_the_target_without_claiming_remote_revocation(self):
        self.pair()
        state = self.connection.forget()
        self.assertEqual(state["state"], "unpaired")
        self.assertEqual(state["keyFingerprint"], self.public["keyFingerprint"])
        self.assertEqual(self.effective_config()["proxycommand"], "/bin/false")
        self.assertEqual(execute("docker", "exec", self.name, "cat", "/tmp/authorized_keys"), self.public["publicKey"])


if __name__ == "__main__":
    unittest.main()
