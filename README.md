<p align="center">
  <img src="icon.svg" alt="Selkies" width="21%">
</p>

# Dev Workspace Desktop on StartOS

> Features not described here follow upstream Selkies and desktop VS Code behavior. User documentation is linked from instructions.md.

This companion provides a browser-streamed desktop editor connected to Dev Workspace through Remote SSH. Native x86 validation covers editing, Node debugging, a Compose Dev Containers workflow, dedicated SSH pairing and companion restart. Full project compatibility and recovery acceptance remain incomplete. The [setup and support guide](instructions.md) covers credentials, pairing, tool locations, application access, recovery, storage expectations and the exact tested configuration.

StartOS provides **Set Keyring Password**, **Unlock Keyring**, and **Keyring Status** actions under **Desktop Keyring**. The keyring password protects saved editor credentials and is independent of the browser password. Changing an existing keyring requires its current password. After a desktop restart, use the Unlock reminder to open the editor. Native x86 checks verify automatic keyring startup, action-driven unlocking, reminder removal and browser reconnection. A disposable native service using the same actions and backend also verifies keyring creation, password changes, rejection of incorrect and superseded passwords, and exact saved-credential preservation after restart. ARM package and isolated Linux backend checks pass; full native ARM StartOS acceptance remains open.

## Table of Contents

Use these sections to locate runtime, storage, setup and recovery details.

- [Image and Container Runtime](#image-and-container-runtime)
- [Volume and Data Layout](#volume-and-data-layout)
- [File Models](#file-models)
- [Dependencies](#dependencies)
- [Network Access and Interfaces](#network-access-and-interfaces)
- [Installation and First-Run Flow](#installation-and-first-run-flow)
- [Editor and Desktop Controls](#editor-and-desktop-controls)
- [Actions](#actions)
- [Tasks](#tasks)
- [Health Checks](#health-checks)
- [Backups and Restore](#backups-and-restore)
- [Limitations and Differences](#limitations-and-differences)
- [Quick Reference for AI Consumers](#quick-reference-for-ai-consumers)

## Image and Container Runtime

The Dockerfile derives from architecture-specific, digest-pinned LinuxServer Selkies images. The desktop subcontainer retains the upstream s6 init system through runAsInit and uses software rendering with Wayland.

The image adds an editor installer and keyring libraries. The user downloads Microsoft desktop VS Code through an explicit setup action into persistent configuration storage. The installer validates the official checksum, release identity, executable architecture, safe extraction paths and license notices. It keeps previous installations when replacing the active version.

The selected installation model is private development on the owner's server. The package contains the installer, not the Microsoft editor, Remote Development extensions or VS Code Server. Those components are obtained through their normal installation paths and retain their own terms and notices. Public package distribution or a hosted editor offering is a separate release decision; this private validation does not establish rights to redistribute Microsoft's components. [Product terms](https://code.visualstudio.com/license), [Remote Development terms and guidance](https://code.visualstudio.com/docs/remote/faq#_license-and-privacy).

The launcher retains the editor sandbox and requests the GNOME Secret Service credential backend. Native x86 StartOS rendered the editor with the sandbox enabled and no host-policy changes. The renderer had zero effective capabilities and NoNewPrivs enabled. Local ARM image results remain separate from native ARM acceptance. No host container socket or Dev Workspace project volume is mounted.

## Volume and Data Layout

Desktop state is separate from development projects. Both declared volumes belong to this companion.

| Volume | Location                                           | Contents                                                                                                |
| ------ | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| main   | Package-managed storage, outside the desktop mount | Desktop access credential and selected editor setup state                                               |
| config | /config                                            | Editor installation, preferences, extensions, keyring, desktop settings and dedicated SSH pairing files |

The editor lives below /config/.local/share/dev-workspace-desktop/editor. Its current link selects a verified version. Earlier versions remain available and consume storage; there is no automatic editor-version cleanup.

Projects and the Podman engine remain in Dev Workspace. Files deliberately saved in the desktop's own /config are companion data, not remote project files.

## File Models

The package seeds main/desktop.json when absent. It stores the desktop password, installed editor version and connection revision; setup actions preserve unknown fields. Pairing actions increment the revision to restart the companion with the selected target.

The dedicated Ed25519 key and pinned workspace host identity live under /config/.ssh/dev-workspace-desktop. A managed Include is prepended to the user's SSH configuration without deleting other hosts. The dev-workspace alias is disabled while unpaired or when its bridge address is unavailable. Invalid persisted state reports an error; Forget Workspace Connection provides a reset without deleting the key.

The main volume is not mounted into the desktop. The upstream password environment interface and StartOS proxy require the current credential. All users of this shared desktop are trusted as one owner. Hand editing the setup state is unsupported because it can claim an editor installation that is absent.

## Dependencies

Dev Workspace version 0.5.0:1 or later is a required running dependency. The companion resolves its ssh binding on internal port 2222 through the SDK bridge-address API, which supplies the assigned address and port. It does not derive the connection from the browser hostname or assume that the preferred external port was assigned.

The interface contract follows the published Dev Workspace source at commit b5632778677d7bc61e0cdbe128af2e550eb7cba4: package ID dev-workspace, host ID ssh, internal port 2222 and user dev. No foreign package source is loaded as a build dependency. Recheck that contract when changing the supported version range.

Missing dependency addresses leave the desktop unpaired or offline. Address changes refresh the managed target and restart the companion; a retained host key is never replaced automatically. The SSH client rejects a replacement host key until the user verifies and pairs it explicitly. These reactive StartOS behaviors still require native acceptance.

Editor installation needs access to the pinned official Microsoft download. Installed editor reuse does not require another download. Extensions and project services have their own connection requirements.

## Network Access and Interfaces

The desktop interface targets the internal HTTP listener on port 3000 and requests StartOS TLS termination. StartOS assigns the actual external ports and controls address reachability; the package does not provision a public route.

The interface is withheld until password and editor setup state exist. The StartOS HTTP authentication gate and upstream desktop gate use the same credential. Native x86 checks verified authenticated HTTPS page access and streaming through both gates, with anonymous requests rejected.

An additional Nginx origin rule permits an HTTPS browser origin only when its hostname and port match the request's Host header. Requests without Origin still require credentials. Local image and native StartOS checks cover anonymous and wrong-password rejection, same-origin access and streaming, and foreign-origin rejection, including another port on the same hostname. A native password rotation closed an existing stream after 760 ms, rejected the old password for the page and streaming upgrade, and restored new access in about ten seconds. These are observations from one run, not a guaranteed deadline. Sustained timeout limits and broader browser behavior still need validation.

## Installation and First-Run Flow

Setup establishes the access credential and downloads the selected editor before normal startup. Editor download and extraction are bounded; the installer requires enough free space for staging and does not remove the previously active installation after a failed update.

While the companion is running, open Actions → Desktop Keyring → Set Keyring Password. For a new keyring, leave Current Keyring Password empty and choose and confirm a password of at least 12 characters. Changing an existing keyring requires its current password. After a restart, use Unlock Keyring before opening the editor. Set Desktop Password controls browser access separately. No operator desktop profile or account credentials are imported.

The desktop starts VS Code automatically. Once paired and with Remote SSH installed, it opens the selected remote folder after any keyring unlock. Otherwise it opens the connection guide. Native x86 restart validation preserved a changed editor theme and font size, all four installed remote-development extensions, the dedicated key and the pinned target. VS Code normalized the selected theme name from `Default Light Modern` to `Light Modern` while retaining its visible appearance. A disposable UI extension credential also survived a native companion restart and browser reconnect through VS Code SecretStorage. Real account sign-in and extension-specific credential flows remain separate acceptance requirements.

## Editor and Desktop Controls

The pinned desktop is deliberately configured for the editor workflow.

| Component                              | Intended behavior                                                                                                                                                 |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VS Code Explorer and file dialogs      | Browse the current editor environment. A Remote SSH folder belongs to Dev Workspace; local files belong to this companion.                                        |
| VS Code terminal                       | Run project commands in the connected workspace. A local editor window has a local companion terminal.                                                            |
| VS Code built-in Browser               | Open forwarded applications inside the desktop. No standalone browser is installed.                                                                               |
| Standalone file manager                | None is installed.                                                                                                                                                |
| Standalone terminal launchers          | The base image retains Foot, XTerm and st files, but desktop hardening disables their execution. Native attempts as the desktop user fail with permission denied. |
| Desktop application menu               | Empty under desktop hardening.                                                                                                                                    |
| Window controls                        | Retained for minimizing, maximizing, fullscreen, window arrangement and closing. The native title-bar menu remains available.                                     |
| Keyring dialogs and certificate viewer | Retained for editor credential and certificate interaction.                                                                                                       |
| sudo                                   | Disabled in the desktop. A native noninteractive attempt fails with permission denied.                                                                            |
| Streaming sidebar                      | Retained for display, audio, clipboard, connection controls and the owner's Viewer mode described below.                                                          |

These settings simplify the desktop; they do not isolate users sharing one session. VS Code can execute code and open terminals. Closing the browser disconnects that viewer, while closing the editor window closes the application. If the last editor window is closed, restart the companion from StartOS to launch it again. Save work before restarting.

The sidebar's Viewer link opens the same desktop with `#shared` in its address. Native Chromium checks show that this mode displays owner edits while suppressing editor input. It still requires the desktop credential. Anyone holding that credential can remove the fragment and open the normal control view, so the link does not grant a separately restricted guest account. Use it only within the existing trusted-owner model. Anonymous and wrong-password viewer requests are rejected, and a foreign browser origin cannot open the viewer stream. [Upstream sharing behavior](https://docs.linuxserver.io/selkies/user-guide/web-client/#sharing).

## Actions

Password generation is both the initial setup and recovery path. Repeating it replaces the access credential and reactively restarts this companion. Native checks confirmed rejection of the previous credential and closure of the open stream. Rotation does not change the separate keyring password. After the companion returns, use the new desktop credential and unlock the retained keyring when prompted.

Editor installation is safe to repeat for the same intact release: it verifies the retained installation and reuses it. A new selected release downloads into staging, verifies it, and then changes the active link. Settings and extensions are outside the version directory. Failed downloads, invalid archives and checksum failures leave the previous active installation selected.

The package maintainer pins editor releases in assets/editor-releases.json. The owner applies that selected release through Install Desktop VS Code while the companion is stopped; a package upgrade alone does not invoke the download. VS Code manages extension updates independently. The [update instructions](instructions.md#updating-the-editor-and-extensions) describe those controls and retained-version storage. Tested version combinations describe the recorded environment, not every later automatic extension update.

Prepare Workspace Key creates or displays the companion's public key. The user authorizes it through Dev Workspace's existing Add SSH Key action. Connect to Dev Workspace takes an independently obtained host fingerprint and a project-folder selection, discovers the endpoint, verifies an actual SSH login and existing folder, then records the connection. It restarts only this companion.

Workspace Connection Status refreshes the address and tests the pinned host, SSH authorization and selected folder. It is an explicit check rather than a recurring SSH health probe. Forget Workspace Connection disables the local target while retaining its key. Rotate Workspace Key replaces that key and removes the local connection, requiring another authorization. Both actions restart the companion. Neither removes the old authorization from Dev Workspace: the result identifies the fingerprint to revoke through Remove SSH Key. Existing authenticated sessions need separate termination.

When paired and Remote SSH is installed normally in the editor, the launcher opens the selected remote folder. Otherwise it opens connection instructions. Remote terminals and workspace extensions belong to Dev Workspace; UI extensions remain in the companion. The package neither bundles extension archives nor installs a second container engine.

Use Terminal > New Terminal for the normal remote shell and verify that `whoami` returns `dev`. VS Code also exposes an explicitly local integrated terminal, which runs as `abc` in the companion even inside a remote window. Developer: Show Running Extensions identifies execution placement: native checks observed Remote SSH and Dev Containers locally, with Codex and Git on the SSH host. Shared Projects opened remotely without trusting the entire provider tree; executable checks used a disposable trusted local project. Coding-agent authentication and workflows retain their separate acceptance requirements.

## Tasks

Initial setup requires an access password and a recorded editor installation. Missing either creates a critical task and prevents startup and interface publication. When a valid installed version differs from the selected release, the companion remains accessible and shows an important update reminder. The initial installation task is cleared so it cannot block the retained editor. A successful update clears the reminder.

A successful setup record is not a complete runtime health check. If editor files are later removed or damaged, the launcher reports the missing installation and the installer reports invalid retained content instead of silently replacing it.

## Health Checks

Desktop Web Endpoint checks whether port 3000 accepts connections. A failure indicates the web listener is unavailable.

A successful listener check does not prove that the editor rendered, the keyring unlocked, an SSH connection succeeded or an extension works. Those outcomes have separate acceptance checks.

## Backups and Restore

The backup declaration includes main and config. This includes the desktop credential, editor installation, preferences, extensions, keyring, pairing private key and pinned host identity. The private key is readable only by the desktop user and is not returned by actions.

Native backup and isolated restore have not been validated. Unsaved buffers and running GUI processes are not recoverable from a file backup. Dev Workspace and its file providers require their own backups. A restored companion with duplicated credentials must be handled deliberately before connecting it to the original workspace.

## Limitations and Differences

Revision `0.1.0:2` passed installed x86 Chromium tests for Command shortcuts, continued typing, saving and reconnect. Revision `0.1.0:4` passed x86 StartOS keyring and desktop access checks. Native ARM StartOS operation and complete lifecycle recovery remain open.

Native x86 checks cover current dependency discovery, all pairing actions, exact remote file bytes, identity persistence, rotation and revocation. VS Code 1.145.3 with Remote SSH 0.128.0 ran a Node debugger, a behavioral test, Git staging and actual Podman/Docker-compatible containers through the remote terminal. Dev Containers 0.473.0 also completed a Node/Compose workflow with edits, tests, a debugger breakpoint, a forwarded HTTP page, rebuild and reconnect. Project files retained workspace ownership. A disposable S9PK built through the streamed terminal passed manifest, architecture and packaged-filesystem checks. The separate Dev Workspace maintained-wrapper build also passed on native x86; it does not replace shared-provider, address-change or broader project acceptance. Opening a local desktop folder does not provide Dev Workspace's runtimes, Podman or package manager.

The native browser record uses Chromium 159.0.8154.6 and Firefox 159.0 with StartOS 0.4.2. Both reached the desktop and passed resize, UTF-8 clipboard round trips, reconnect and roughly ten minutes of streaming. The original `0.1.0:1` release could focus the editor menu after a macOS Command shortcut. On macOS, both browsers saved with left and right Command on the corrected desktop. Firefox also saved with Ctrl and continued typing and saving after reconnect. Safari/WebKit remains unverified. The [support guide](instructions.md#candidate-limitations) distinguishes these results from completed native recovery.

Native resource sampling of revision `0.1.0:1` observed about 1.28 GiB proportional RAM while idle and a 1.33 GiB peak during a single 1440x1000 Chromium session alongside Rails, frontend and container workloads. Companion CPU averaged 1.64% of one logical CPU while idle and 62.97% during concurrent editing, with a sampled peak of 229.36%. Project processes and container memory are additional. Its persistent configuration occupied about 1.08 GiB and showed no net allocated growth across the three short sample windows. Eleven exact editor saves, browser disconnect/reconnect and 2,541 application responses passed. These observations do not establish a minimum server specification, capacity for larger displays or additional viewers, or enforced CPU/RAM quotas. The [resource guide](instructions.md#resource-expectations) explains storage scope and measurement limits.

This package streams desktop VS Code. [code-server](https://coder.com/docs/code-server) and [OpenVSCode Server](https://github.com/gitpod-io/openvscode-server/blob/main/README.md) serve their editor interfaces directly to browsers and remain separate alternatives. This companion does not install them.

The desktop remains a single-owner session. Its window controls and streaming sidebar are present; it is not a kiosk or an isolation boundary between users. Native checks confirm disabled standalone terminals and sudo. Revision `0.1.0:1` uses the explicit `none` setting to disable file transfers. The initial `0.1.0:0` empty setting disappeared during startup, and a native authenticated upload was accepted. Updated ARM and emulated x86 image checks reject uploads, downloads and file browsing with HTTP 403 while preserving authenticated streaming. The corrected x86 package also passed those checks through StartOS after upgrade, with editor settings, extensions and pairing preserved. The image also requests disabled Docker startup, gamepads, webcam, printing and sidebar command execution; acceptance of those other controls remains open.

Keyring creation and manual unlock after restart were observed locally and on native x86 StartOS. A disposable UI extension stored a random value through VS Code SecretStorage and retrieved the same value after rotation, companion restart and browser reconnect. Its persisted editor database entry used Chromium v11 ciphertext, and retrieval resumed after the existing keyring was unlocked. The fixture credential and extension were removed through their normal APIs. This validates the tested SecretStorage path; actual external-account sign-in and every extension's chosen storage method remain unverified. GPU acceleration and additional streaming transports are outside the initial scope.

Microsoft editor, extension and server terms are separate from the Selkies base license. Public distribution or a hosted service offering requires its own review. The package does not bundle extension archives or VS Code Server.

## Quick Reference for AI Consumers

This inventory describes the current candidate. The acceptance limits above apply to its advertised workflows and architectures.

```yaml
package_id: dev-workspace-desktop
image: ghcr.io/linuxserver/baseimage-selkies
architectures: [x86_64, aarch64]
subcontainers: [desktop]
volumes:
  main: package-managed
  config: /config
file_models:
  - main/desktop.json
startos_managed_env_vars: [PUID, PGID, CUSTOM_USER, PASSWORD]
dependencies:
  dev-workspace: { version: '>=0.5.0:1', kind: running }
interfaces:
  desktop: { type: ui, port: 3000 }
actions:
  [
    set-desktop-password,
    install-editor,
    prepare-workspace-key,
    connect-workspace,
    workspace-connection-status,
    forget-workspace,
    rotate-workspace-key,
  ]
tasks:
  - { action: set-desktop-password, severity: critical }
  - { action: install-editor, severity: critical, when: no-installed-editor }
  - {
      action: install-editor,
      severity: important,
      when: editor-update-available,
    }
health_checks: [desktop]
```
