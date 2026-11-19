#!/usr/bin/env python3
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request


ARCHITECTURES = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}
DOWNLOAD_HOSTS = {"vscode.download.prss.microsoft.com", "update.code.visualstudio.com"}
MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_EXTRACTED = 2 * 1024 * 1024 * 1024


def require_download_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in DOWNLOAD_HOSTS
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("The editor download must use an approved Microsoft HTTPS address.")


class MicrosoftRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        require_download_url(url)
        return super().redirect_request(request, response, code, message, headers, url)


def validate_release(release):
    if release.get("architecture") not in ("x64", "arm64"):
        raise ValueError("Unsupported editor architecture.")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", release.get("version", "")):
        raise ValueError("Invalid editor version.")
    if not re.fullmatch(r"[a-f0-9]{40}", release.get("commit", "")):
        raise ValueError("Invalid editor revision.")
    if not re.fullmatch(r"[a-f0-9]{64}", release.get("sha256", "")):
        raise ValueError("Invalid editor checksum.")
    require_download_url(release["url"])


def download_editor(release, destination):
    digest = hashlib.sha256()
    total = 0
    request = urllib.request.Request(release["url"], headers={"User-Agent": "Dev-Workspace-Desktop"})
    opener = urllib.request.build_opener(MicrosoftRedirect())
    with opener.open(request, timeout=30) as response, destination.open("xb") as output:
        if response.status != 200:
            raise ValueError("The editor download did not return a successful response.")
        require_download_url(response.geturl())
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_DOWNLOAD:
                raise ValueError("The editor download exceeds its size limit.")
            digest.update(chunk)
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())
    if digest.hexdigest() != release["sha256"]:
        raise ValueError("The editor download checksum does not match the selected release.")


def verify_editor(directory, release):
    product = json.loads((directory / "resources/app/product.json").read_text())
    package = json.loads((directory / "resources/app/package.json").read_text())
    if product.get("commit") != release["commit"] or package.get("version") != release["version"]:
        raise ValueError("The editor archive does not contain the selected release.")
    binary = directory / "code"
    with binary.open("rb") as stream:
        header = stream.read(20)
    machine = 62 if release["architecture"] == "x64" else 183
    if header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != machine:
        raise ValueError("The editor executable has the wrong architecture.")
    for relative in ("code", "bin/code"):
        candidate = directory / relative
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise ValueError("The editor archive is missing an executable.")
    for relative in ("resources/app/LICENSE.rtf", "resources/app/ThirdPartyNotices.txt", "LICENSES.chromium.html"):
        candidate = directory / relative
        if not candidate.is_file() or candidate.stat().st_size == 0:
            raise ValueError("The editor archive is missing its license notices.")


def extract_editor(archive, destination, release):
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        if not members or len(members) > 30000 or sum(member.size for member in members) > MAX_EXTRACTED:
            raise ValueError("The editor archive exceeds its extraction limits.")
        roots = set()
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or not name.parts:
                raise ValueError("The editor archive contains an unsafe path.")
            roots.add(name.parts[0])
            if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValueError("The editor archive contains an unsupported file type.")
            tarfile.data_filter(member, str(destination))
        if len(roots) != 1:
            raise ValueError("The editor archive must contain one application directory.")
        source.extractall(destination, members=members, filter="data")
    directory = destination / roots.pop()
    verify_editor(directory, release)
    return directory


def activate(root, target):
    temporary = root / f".current-{os.getpid()}"
    try:
        temporary.symlink_to(target.relative_to(root), target_is_directory=True)
        os.replace(temporary, root / "current")
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def install_editor(root, release):
    validate_release(release)
    root = Path(root)
    if root.is_symlink():
        raise ValueError("The editor installation directory cannot be a symbolic link.")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    versions = root / "versions"
    if versions.is_symlink():
        raise ValueError("The editor versions directory cannot be a symbolic link.")
    versions.mkdir(exist_ok=True, mode=0o700)
    lock_fd = os.open(root / "install.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another editor installation is already running.") from error
        target = versions / f"{release['commit']}-{release['architecture']}"
        if target.is_symlink():
            raise ValueError("The selected editor directory cannot be a symbolic link.")
        if target.exists():
            verify_editor(target, release)
            if json.loads((target / ".workspace-editor.json").read_text()) != release:
                raise ValueError("The installed editor provenance does not match the selected release.")
            activate(root, target)
            return {"status": "ready", "version": release["version"], "architecture": release["architecture"]}
        if shutil.disk_usage(root).free < MAX_DOWNLOAD + MAX_EXTRACTED:
            raise ValueError("The editor installation requires at least 2.5 GiB of free storage.")
        with tempfile.TemporaryDirectory(prefix=".install-", dir=root) as temporary:
            stage = Path(temporary)
            archive = stage / "editor.tar.gz"
            download_editor(release, archive)
            unpacked = stage / "unpacked"
            unpacked.mkdir(mode=0o700)
            directory = extract_editor(archive, unpacked, release)
            (directory / ".workspace-editor.json").write_text(json.dumps(release, sort_keys=True) + "\n")
            os.rename(directory, target)
        activate(root, target)
        return {"status": "installed", "version": release["version"], "architecture": release["architecture"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="/config/.local/share/dev-workspace-desktop/editor")
    parser.add_argument("--architecture", default=os.uname().machine, choices=tuple(ARCHITECTURES))
    options = parser.parse_args()
    releases = json.loads(Path(__file__).with_name("editor-releases.json").read_text())
    release = releases[ARCHITECTURES[options.architecture]]
    try:
        print(json.dumps(install_editor(options.root, release)))
    except (OSError, ValueError, tarfile.TarError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
