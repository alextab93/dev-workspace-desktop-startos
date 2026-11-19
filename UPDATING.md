# Updating Dev Workspace Desktop

The runtime has two independent inputs: the LinuxServer Selkies base image and the Microsoft editor downloaded during explicit user setup. Keep their provenance separate.

## Selkies base

The architecture-specific FROM lines in Dockerfile pin the base image by digest. Inspect upstream release metadata, source entrypoint/init behavior and both registry manifests before changing those pins. Recheck environment variable support, desktop startup, Nginx template layout and the editor's native libraries.

The current source reference is linuxserver/docker-baseimage-selkies commit e45b4fe636ee99860a40eb552d0e4b21aefad842. The icon is the upstream Selkies asset docs/assets/logo/selkies.svg from selkies-project/selkies commit d6b9351421bd503ffa89bdee78e2bce758b1ffe5, with XML comments removed without altering its drawing. Preserve the applicable upstream license and notices.

The Nginx template includes assets/desktop-origin.conf in both server blocks. Validate the resulting configuration and actual same-origin/foreign-origin HTTP and streaming behavior after an upstream template change. Do not weaken the origin rule to accommodate a proxy without first establishing which external host and port it forwards.

The pinned client's macOS Command mapping briefly sends Alt before switching to Ctrl. In desktop VS Code this focuses the menu bar and consumes subsequent typing. The build applies `assets/patch-selkies-keyboard.py` to the dashboard client so the enabled Command-as-Ctrl option sends Ctrl immediately for either Command key. Upstream initialization copies that dashboard into the served `web` directory on each start. Verify the served client after startup and restart when changing the base image. Disabling that option preserves the upstream Super mapping. The patch requires the exact inspected bundle hash and fails the build if the client changes. Review the upstream fix and remove this correction when a newly pinned image passes the same real-editor behavior: Command and Ctrl selection, copy, paste, save, continued typing, both Command keys, and reconnect without lost characters or unexpected menu focus.

## Editor release

Fetch the official Microsoft update metadata for linux-x64 and linux-arm64 from update.code.visualstudio.com. Update assets/editor-releases.json with the selected version, commit, official archive URL and SHA256 for each architecture. Keep both architectures on the same intended release.

Download and verify the actual archives before updating the candidate. Inspect product metadata, ELF architecture and the retained notices at resources/app/LICENSE.rtf, resources/app/ThirdPartyNotices.txt and LICENSES.chromium.html. A constructed test archive is not proof of the current official layout.

The installer stores selected versions in config and changes the current link only after verification. Test initial installation, offline reuse and preservation of the previous editor after download, checksum or extraction failure. Keep user preferences, extensions and pairing data outside installation directories. Verify that the package startup and interface gates still permit the retained editor after an unsuccessful update, and that only an important update task remains. Archive preservation alone does not prove usable recovery. Missing first installation must remain critical.

Use two real official releases to validate an update on each advertised archive architecture. Keep the previous version's full file inventory and user-data fixture unchanged after failed updates, then verify the selected version after success. Prove offline behavior with a disposable network namespace or another actual network boundary. Constructed archive tests remain useful for malformed tar and unsafe-path cases, but do not replace installation of the official archives. Archive validation on x86 does not establish ARM runtime support.

Record the editor, Remote SSH and Dev Containers versions used for native acceptance. The package pins the editor; users install and update extensions through VS Code. A package release must not silently override their extension settings. The public instructions explain how owners apply the selected editor release and retain a tested extension version.

Do not copy Microsoft archives, installed editor files, extension archives or VS Code Server into the Docker context or S9PK. Private investigation material belongs outside the public payload. Inspect every final image layer, not only the merged filesystem.

For a distribution review, record the exact product and installed extension terms and retain all shipped notices. Keep private installation, redistribution of Microsoft components, distribution of this wrapper and a hosted editor service as separate decisions. The current private-use approach does not resolve the later public release gate. [Product terms](https://code.visualstudio.com/license), [Remote Development guidance](https://code.visualstudio.com/docs/remote/faq#_license-and-privacy), [Marketplace terms](https://aka.ms/vsmarketplace-ToU).

## Checks

Run the focused checks from this repository:

```sh
python3 -B tests/editorInstaller.test.py
node --test tests/desktopSetup.test.cjs tests/desktopStream.test.mjs
WORKSPACE_TEST_IMAGE=dev-workspace:qa-reproducible python3 -B tests/workspaceConnection.test.py
npx tsc --noEmit
node node_modules/@start9labs/start-sdk/lint.mjs
npx prettier --check startos tests/desktopGateway.test.mjs tests/desktopSetup.test.cjs tests/desktopSetup.entry.ts tests/desktopStream.test.mjs assets/editor-releases.json
docker build --platform linux/arm64 --build-arg TARGETARCH=arm64 -t dev-workspace-desktop:test-arm .
DESKTOP_TEST_IMAGE=dev-workspace-desktop:test-arm node --test tests/desktopGateway.test.mjs
DESKTOP_TEST_IMAGE=dev-workspace-desktop:test-arm WORKSPACE_TEST_IMAGE=dev-workspace:qa-reproducible python3 -B tests/desktopPairing.test.py
```

The gateway test owns a disposable loopback-only container and removes it afterward. It checks real authentication responses and WebSocket upgrades; it does not establish editor rendering or StartOS behavior.

The desktop setup suite bundles the current source into a temporary directory using the locked SDK toolchain, exercises real settings files, and removes its fixture afterward. It verifies first-install requirements, retained-editor access, update reminders, invalid state and password recovery through simulated StartOS task/interface effects. It needs no Docker image, server credentials or private evidence files. These source checks do not establish native editor startup or a completed StartOS upgrade.

Build the workspace fixture image from the Dev Workspace checkout using its documented Docker build command before running pairing tests. The pairing suites use unique owned containers; the packaged-client test also owns an isolated network and volume. They create disposable SSH keys, exercise real authorization and file writes, and remove their fixtures. Without the image environment variables the relevant cases are skipped, which is not an integration pass. The packaged client runs as the desktop user; it does not replace a real Remote SSH editor or native StartOS check.

The service connection uses an explicit interface contract verified against Dev Workspace commit b5632778677d7bc61e0cdbe128af2e550eb7cba4. Recheck its package ID, SSH host ID, internal port, account and minimum version in startos/utils.ts when that package changes. The dependency icon is copied from that package's icon.svg. Keep address discovery reactive and host-key verification strict; do not add a guessed endpoint fallback.

Build and inspect each advertised S9PK after source checks. Use the Makefile packaging targets, which reject generated Python caches in assets. Before a direct start-cli packaging command, run `make check-assets`. Git and Docker ignore rules do not filter the separate S9PK assets archive. Remove stale generated caches before packaging and inspect the complete packaged asset inventory for extra files or local paths. The helper tests disable bytecode writes when loading asset modules.

Record exact artifact and image hashes. On an authorized isolated native fixture, open the real interface, save and reopen a file, exercise authentication rotation and streaming, pair with Dev Workspace, run the claimed project/container workflow, restart, and validate backup/restore. Use native hardware for architecture claims.

Preserve the normal editor sandbox. Diagnose namespace and shared-memory failures before considering any permission change. Do not package a local Docker seccomp profile as an assumed StartOS solution.

## Version and release data

Update startos/versions/current.ts with accurate release notes in every supported locale. Preserve migrations that perform work in their versioned files. Keep README and instructions aligned with verified behavior and update the tested editor/extension matrix.

The companion repository URL in the manifest names the intended repository. Repository creation, commits, publishing and registry submission require their applicable authorization. This candidate has not completed those delivery steps.
