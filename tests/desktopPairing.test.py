import json
import os
import subprocess
import time
import unittest
import uuid


HELPER = '/usr/local/lib/dev-workspace-desktop/workspace-connection.py'


def execute(*arguments, input=None, check=True):
    return subprocess.run(arguments, input=input, capture_output=True, text=True, timeout=45, check=check)


@unittest.skipUnless(os.environ.get('DESKTOP_TEST_IMAGE') and os.environ.get('WORKSPACE_TEST_IMAGE'), 'Set both disposable test image names.')
class DesktopPairingBehavior(unittest.TestCase):
    def setUp(self):
        self.marker = uuid.uuid4().hex
        self.network = 'scratch-desktop-pairing-net-' + self.marker
        self.volume = 'scratch-desktop-pairing-config-' + self.marker
        self.client = 'scratch-desktop-pairing-client-' + self.marker
        self.server = 'scratch-desktop-pairing-server-' + self.marker
        self.resources = []
        self.addCleanup(self.cleanup)
        execute('docker', 'network', 'create', '--label', 'dev-workspace-fixture=' + self.marker, self.network)
        self.resources.append(('network', self.network))
        execute('docker', 'volume', 'create', '--label', 'dev-workspace-fixture=' + self.marker, self.volume)
        self.resources.append(('volume', self.volume))
        command = "mkdir -p /run/sshd /home/dev/projects; chown dev:dev /home/dev/projects; test -f /tmp/workspace-host || ssh-keygen -q -t ed25519 -N '' -f /tmp/workspace-host; exec /usr/sbin/sshd -D -e -p 2222 -h /tmp/workspace-host -o AuthorizedKeysFile=/tmp/authorized_keys -o StrictModes=no -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o PermitRootLogin=no -o AllowUsers=dev -o UsePAM=no"
        execute('docker', 'create', '--name', self.server, '--label', 'dev-workspace-fixture=' + self.marker, '--network', self.network, '--entrypoint', '/bin/sh', os.environ['WORKSPACE_TEST_IMAGE'], '-c', command)
        self.resources.append(('container', self.server))
        execute('docker', 'start', self.server)
        execute('docker', 'create', '--name', self.client, '--label', 'dev-workspace-fixture=' + self.marker, '--network', self.network, '--mount', f'type=volume,source={self.volume},target=/config,volume-nocopy', '--entrypoint', 'sleep', os.environ['DESKTOP_TEST_IMAGE'], 'infinity')
        self.resources.append(('container', self.client))
        execute('docker', 'start', self.client)
        execute('docker', 'exec', self.client, 'chown', 'abc:abc', '/config')
        self.refresh_server_address()

    def refresh_server_address(self):
        info = json.loads(execute('docker', 'inspect', self.server).stdout)[0]
        self.endpoint = info['NetworkSettings']['Networks'][self.network]['IPAddress'] + ':2222'
        for _ in range(50):
            result = execute('docker', 'exec', self.server, 'ssh-keygen', '-lf', '/tmp/workspace-host.pub', check=False)
            if result.returncode == 0:
                self.fingerprint = result.stdout.split()[1]
                return
            time.sleep(0.1)
        raise AssertionError('The fixture did not create its host identity.')

    def client_command(self, *arguments, check=True):
        return execute('docker', 'exec', '--user', 'abc', self.client, *arguments, check=check)

    def helper(self, *arguments):
        return json.loads(self.client_command('python3', HELPER, *arguments).stdout)

    def authorize(self, public_key):
        execute('docker', 'exec', '-i', self.server, 'sh', '-c', 'cat > /tmp/authorized_keys; chmod 644 /tmp/authorized_keys', input=public_key + '\n')

    def pair(self):
        return self.helper('pair', '--endpoint', self.endpoint, '--fingerprint', self.fingerprint, '--folder', '/home/dev/projects')

    def cleanup(self):
        for kind, name in reversed(self.resources):
            info = json.loads(execute('docker', kind, 'inspect', name).stdout)[0]
            labels = info['Config']['Labels'] if kind == 'container' else info['Labels']
            if labels.get('dev-workspace-fixture') != self.marker:
                raise AssertionError('Refusing to remove a fixture with a different owner.')
            arguments = ['docker', kind, 'rm']
            if kind == 'container':
                arguments += ['--force', '--volumes']
            execute(*arguments, name)

    def test_packaged_desktop_key_edits_remote_files_and_retains_trust_through_restart(self):
        self.assertEqual(self.client_command('id', '-un').stdout, 'abc\n')
        self.assertEqual(self.client_command('id', '-u').stdout, '911\n')
        self.assertEqual(self.helper('refresh')['state'], 'unpaired')
        public = self.helper('key')
        self.assertEqual(self.client_command('stat', '-c', '%a', '/config/.ssh/dev-workspace-desktop/identity/id_ed25519').stdout, '600\n')
        self.authorize(public['publicKey'])
        paired = self.pair()
        self.assertEqual(paired['state'], 'paired')
        self.assertEqual(paired['hostFingerprint'], self.fingerprint)
        self.assertTrue(self.helper('check')['verified'])
        self.client_command('ssh', 'dev-workspace', "printf 'Remote desktop project\n' > /home/dev/projects/desktop-pairing.txt")
        expected = 'Remote desktop project\n'
        self.assertEqual(execute('docker', 'exec', self.server, 'cat', '/home/dev/projects/desktop-pairing.txt').stdout, expected)
        execute('docker', 'restart', self.client)
        self.assertEqual(self.helper('status')['keyFingerprint'], public['keyFingerprint'])
        self.assertEqual(self.client_command('ssh', 'dev-workspace', 'cat /home/dev/projects/desktop-pairing.txt').stdout, expected)
        self.assertEqual(self.helper('refresh')['state'], 'offline')
        self.assertNotEqual(self.client_command('ssh', '-o', 'BatchMode=yes', 'dev-workspace', 'true', check=False).returncode, 0)
        self.helper('refresh', '--endpoint', self.endpoint)
        self.assertTrue(self.helper('check')['verified'])
        rotated = self.helper('rotate')
        self.assertEqual(rotated['previousFingerprint'], public['keyFingerprint'])
        denied = self.client_command('python3', HELPER, 'pair', '--endpoint', self.endpoint, '--fingerprint', self.fingerprint, check=False)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn('Permission denied', denied.stderr)
        self.authorize(rotated['publicKey'])
        self.assertEqual(self.pair()['keyFingerprint'], rotated['keyFingerprint'])
        self.authorize('')
        denied = self.client_command('python3', HELPER, 'check', check=False)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn('Permission denied', denied.stderr)
        self.assertEqual(self.helper('forget')['state'], 'unpaired')


if __name__ == '__main__':
    unittest.main()
