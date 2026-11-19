#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path('/usr/local/lib/dev-workspace-desktop')
EDITOR = Path('/config/.local/share/dev-workspace-desktop/editor/current/bin/code')
GUIDE = '/usr/local/share/dev-workspace-desktop/connect-workspace.txt'


def arguments():
    try:
        status = subprocess.run(
            ['python3', str(ROOT / 'workspace-connection.py'), 'status'],
            capture_output=True, text=True, timeout=15, check=True,
        )
        connection = json.loads(status.stdout)
        if connection.get('state') != 'paired':
            return [GUIDE]
        extensions = subprocess.run(
            [str(EDITOR), '--list-extensions'],
            capture_output=True, text=True, timeout=30, check=True,
        )
        if 'ms-vscode-remote.remote-ssh' not in extensions.stdout.lower().splitlines():
            return [GUIDE]
        folder = connection.get('folder')
        if folder not in ('/home/dev/projects', '/projects-shared'):
            raise ValueError('Unsupported remote project folder.')
        return ['--remote', 'ssh-remote+dev-workspace', folder]
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Open Dev Workspace: ' + str(error), file=sys.stderr)
        return [GUIDE]


if __name__ == '__main__':
    os.execv('/usr/local/bin/code', ['code', *arguments()])
