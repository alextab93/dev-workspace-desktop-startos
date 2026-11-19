import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("installer", Path(__file__).parents[1] / "assets/install-editor.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def fixture_archive(commit="a" * 40, version="1.0.0", machine=183, extra=None):
    binary = bytearray(20)
    binary[:6] = b"\x7fELF\x02\x01"
    binary[18:20] = machine.to_bytes(2, "little")
    files = {
        "code": (bytes(binary), 0o755),
        "bin/code": (b"#!/bin/sh\nexit 0\n", 0o755),
        "resources/app/product.json": (json.dumps({"commit": commit}).encode(), 0o644),
        "resources/app/package.json": (json.dumps({"version": version}).encode(), 0o644),
        "resources/app/LICENSE.rtf": (b"{\\rtf1 Fixture license}\n", 0o644),
        "resources/app/ThirdPartyNotices.txt": (b"Fixture notices\n", 0o644),
        "LICENSES.chromium.html": (b"<html>Fixture Chromium notices</html>\n", 0o644),
    }
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, (content, mode) in files.items():
            member = tarfile.TarInfo("VSCode-linux-arm64/" + name)
            member.mode = mode
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        if extra is not None:
            archive.addfile(extra, io.BytesIO(b"x") if extra.size else None)
    return output.getvalue()


class Download(io.BytesIO):
    status = 200

    def geturl(self):
        return "https://vscode.download.prss.microsoft.com/fixture.tar.gz"


class EditorInstallerBehavior(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "editor"
        self.archive = fixture_archive()
        self.release = {
            "architecture": "arm64",
            "version": "1.0.0",
            "commit": "a" * 40,
            "url": "https://vscode.download.prss.microsoft.com/fixture.tar.gz",
            "sha256": hashlib.sha256(self.archive).hexdigest(),
        }

    def install(self, release=None, archive=None):
        with patch("urllib.request.OpenerDirector.open", return_value=Download(self.archive if archive is None else archive)):
            return installer.install_editor(self.root, self.release if release is None else release)

    def test_installs_verified_editor_and_preserves_notices(self):
        self.assertEqual(self.install(), {"status": "installed", "version": "1.0.0", "architecture": "arm64"})
        current = self.root / "current"
        self.assertEqual((current / "resources/app/LICENSE.rtf").read_bytes(), b"{\\rtf1 Fixture license}\n")
        self.assertEqual((current / "resources/app/ThirdPartyNotices.txt").read_bytes(), b"Fixture notices\n")
        self.assertEqual((current / "LICENSES.chromium.html").read_bytes(), b"<html>Fixture Chromium notices</html>\n")
        self.assertTrue(os.access(current / "bin/code", os.X_OK))
        self.assertEqual(json.loads((current / ".workspace-editor.json").read_text()), self.release)
        self.assertEqual(list(self.root.glob(".install-*")), [])

    def test_existing_valid_installation_works_without_network(self):
        self.install()
        with patch("urllib.request.OpenerDirector.open", side_effect=OSError("Offline")):
            result = installer.install_editor(self.root, self.release)
        self.assertEqual(result["status"], "ready")
        self.assertEqual((self.root / "current/resources/app/LICENSE.rtf").read_bytes(), b"{\\rtf1 Fixture license}\n")

    def test_failed_update_retains_previous_editor_and_user_settings(self):
        self.install()
        previous = (self.root / "current").resolve()
        settings = self.root.parent / "user-settings.json"
        settings.write_bytes(b'{"editor.fontSize":18}\n')
        release = dict(self.release, commit="b" * 40, version="1.0.1", sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.install(release)
        self.assertEqual((self.root / "current").resolve(), previous)
        self.assertEqual(settings.read_bytes(), b'{"editor.fontSize":18}\n')
        self.assertEqual(list(self.root.glob(".install-*")), [])

    def test_successful_update_retains_previous_version(self):
        self.install()
        previous = (self.root / "current").resolve()
        archive = fixture_archive(commit="b" * 40, version="1.0.1")
        release = dict(self.release, commit="b" * 40, version="1.0.1", sha256=hashlib.sha256(archive).hexdigest())
        self.assertEqual(self.install(release, archive)["version"], "1.0.1")
        self.assertEqual(json.loads((self.root / "current/resources/app/package.json").read_text())["version"], "1.0.1")
        self.assertEqual((previous / "resources/app/LICENSE.rtf").read_bytes(), b"{\\rtf1 Fixture license}\n")

    def test_wrong_architecture_is_not_activated(self):
        archive = fixture_archive(machine=62)
        release = dict(self.release, sha256=hashlib.sha256(archive).hexdigest())
        with self.assertRaisesRegex(ValueError, "architecture"):
            self.install(release, archive)
        self.assertFalse((self.root / "current").exists())

    def test_wrong_product_is_not_activated(self):
        archive = fixture_archive(version="9.9.9")
        release = dict(self.release, sha256=hashlib.sha256(archive).hexdigest())
        with self.assertRaisesRegex(ValueError, "selected release"):
            self.install(release, archive)
        self.assertFalse((self.root / "current").exists())

    def test_unsafe_archive_cannot_write_outside_staging(self):
        for name, link in (("../../escaped.txt", None), ("VSCode-linux-arm64/link", "../../../../escaped.txt")):
            with self.subTest(name=name):
                extra = tarfile.TarInfo(name)
                if link is not None:
                    extra.type = tarfile.SYMTYPE
                    extra.linkname = link
                else:
                    extra.size = 1
                archive = fixture_archive(extra=extra)
                release = dict(self.release, sha256=hashlib.sha256(archive).hexdigest())
                with self.assertRaises((ValueError, tarfile.FilterError)):
                    self.install(release, archive)
                self.assertFalse((self.root.parent / "escaped.txt").exists())
                self.assertFalse((self.root / "current").exists())
                self.assertEqual(list(self.root.glob(".install-*")), [])

    def test_rejects_non_microsoft_downloads_before_installation(self):
        for url in ("http://vscode.download.prss.microsoft.com/file", "https://example.org/file", "https://user@vscode.download.prss.microsoft.com/file"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "Microsoft HTTPS"):
                self.install(dict(self.release, url=url))
        self.assertFalse(self.root.exists())

    def test_missing_notices_do_not_replace_existing_editor(self):
        self.install()
        current = self.root / "current"
        (current / "resources/app/ThirdPartyNotices.txt").unlink()
        with self.assertRaisesRegex(ValueError, "license notices"):
            self.install()
        self.assertEqual((current / "resources/app/LICENSE.rtf").read_bytes(), b"{\\rtf1 Fixture license}\n")

    def test_missing_chromium_notices_are_reported(self):
        self.install()
        (self.root / "current/LICENSES.chromium.html").unlink()
        with self.assertRaisesRegex(ValueError, "license notices"):
            self.install()
        self.assertEqual((self.root / "current/resources/app/ThirdPartyNotices.txt").read_bytes(), b"Fixture notices\n")

    def test_download_failure_preserves_the_previous_editor(self):
        self.install()
        previous = (self.root / "current").resolve()
        release = dict(self.release, commit="b" * 40, version="1.0.1")
        with patch("urllib.request.OpenerDirector.open", side_effect=OSError("Network unavailable")):
            with self.assertRaisesRegex(OSError, "Network unavailable"):
                installer.install_editor(self.root, release)
        self.assertEqual((self.root / "current").resolve(), previous)
        self.assertEqual(list(self.root.glob(".install-*")), [])

    def test_invalid_update_archive_preserves_the_previous_editor(self):
        self.install()
        previous = (self.root / "current").resolve()
        archive = b"not a gzip archive"
        release = dict(self.release, commit="b" * 40, version="1.0.1", sha256=hashlib.sha256(archive).hexdigest())
        with self.assertRaises(tarfile.ReadError):
            self.install(release, archive)
        self.assertEqual((self.root / "current").resolve(), previous)
        self.assertEqual(list(self.root.glob(".install-*")), [])


if __name__ == "__main__":
    unittest.main()
