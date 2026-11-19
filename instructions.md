# Dev Workspace Desktop

## Documentation

- [Selkies user guide](https://docs.linuxserver.io/selkies/user-guide/*): browser desktop controls and streaming behavior.
- [VS Code Remote SSH](https://code.visualstudio.com/docs/remote/ssh): connecting the desktop editor to a remote development environment.

## Set up the desktop

1. Complete **Set Desktop Password** and save the generated password. The username is **desktop**.
2. Complete **Install Desktop VS Code** to obtain the selected editor from Microsoft. This requires an Internet connection and at least 2.5 GiB of free storage. Review the [Microsoft product terms](https://code.visualstudio.com/license) before continuing.
3. Start the service. In **Actions → Desktop Keyring → Set Keyring Password**, choose and confirm a password of at least 12 characters. Leave the current password empty for the first keyring. Keep this password for future desktop restarts.
4. Open **Desktop VS Code** using the generated desktop credentials. The editor opens after the keyring is unlocked. After a restart, use **Actions → Desktop Keyring → Unlock Keyring** with your keyring password. **Keyring Status** reports whether setup or unlocking is needed.
5. Complete the editor's welcome screen. Account sign-in is optional for ordinary editing.

This workflow is for your own private development environment. Install extensions through the official editor's Extensions view and review their individual terms. Microsoft distinguishes private Remote Development use from public or commercial offerings built on its components. [Remote Development licensing](https://code.visualstudio.com/docs/remote/faq#_license-and-privacy).

The keyring password protects saved editor credentials and is independent of the browser password. **Set Desktop Password** changes browser access and restarts the desktop; it does not change the keyring password. To change an existing keyring password, use **Set Keyring Password** with its current password and the new password twice. Saved credentials are retained. An existing installation keeps its original keyring and requires its existing password. There is no password recovery or reset action that deletes saved credentials. Keep the keyring password in your password manager.

Keyring passwords are used for the requested operation and are not saved in desktop settings or returned in action results. For extensions using VS Code SecretStorage, the desktop editor stores encrypted entries in `/config/.config/Code/User/globalStorage/state.vscdb` and uses the Linux keyring under `/config/.local/share/keyrings/` to decrypt them. Its shared local control socket is restricted to the desktop account. Everyone with access to this single-owner desktop can use its unlocked saved credentials.

StartOS terminates HTTPS for the browser connection. Install and trust your server's certificate authority on the computer using the browser, then open the current address from **Interfaces**. A StartOS dashboard login does not replace the desktop credential. The desktop is shared by everyone holding that credential.

## Updating the editor and extensions

The companion package selects a specific editor release. Updating this StartOS package alone does not download a different editor. When the package selects a newer release, an update reminder appears and you can keep using the installed editor. To update, save your work, stop this companion, run **Install Desktop VS Code**, then start it again. Dev Workspace has its own lifecycle and continues running. Check **Help → About** afterward.

The installer verifies the download before selecting it and retains the previous editor directory. An intact selected installation can be reused offline. A first installation or a different release requires Internet access. If an update reports a download, checksum or archive error, start the companion again to use the previous selected editor. The update reminder remains until installation succeeds. Correct the reported problem before retrying. Retained editor versions consume storage, and there is currently no version-cleanup action.

Editor preferences, extensions, keyring and SSH pairing are stored separately from editor versions. Extension updates are controlled by VS Code, independently of StartOS package updates. Use the Extensions view's per-extension update controls when retaining a tested version, and record the editor, Remote SSH and Dev Containers versions when diagnosing compatibility. [VS Code update settings](https://code.visualstudio.com/docs/supporting/faq#_how-do-i-opt-out-of-vs-code-autoupdates).

## Remote projects

1. Run **Prepare Workspace Key** in this companion. Copy its public key.
2. In Dev Workspace, use **Add SSH Key** to authorize that key. Give it a label identifying this desktop.
3. Copy the **Ed25519 SHA256 host fingerprint** from Dev Workspace's **Connection Information**.
4. Run **Connect to Dev Workspace** in the companion. Enter that fingerprint and choose **Local Projects** or **Shared Projects**. The address and port are discovered automatically. Shared Projects requires a configured, available provider folder.
5. Open the desktop editor and install **Remote - SSH** by Microsoft from its Extensions view. Open the Command Palette, select **Remote-SSH: Connect to Host**, and choose **dev-workspace**.
6. Open `/home/dev/projects` or `/projects-shared` on that remote host. Check the editor's remote indicator before running project commands. Once paired with the extension installed, later desktop starts open the selected remote folder automatically.

The remote window uses Dev Workspace's terminals, runtimes, Podman and package tools. Keep container projects in **Local Projects**. Your selected Nextcloud or FileBrowser files remain owned by their provider. Opening a local desktop folder uses this companion's environment instead.

| Work                                                                        | Where it runs or lives                                                |
| --------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Editor windows, themes, keyring and browser streaming                       | This desktop companion                                                |
| The normal terminal from **Terminal > New Terminal** in a Remote SSH window | Dev Workspace as `dev`                                                |
| An explicitly selected **Create New Integrated Terminal (Local)**           | This desktop companion as `abc`, including inside a Remote SSH window |
| Local project source, runtimes, dependencies and package builds             | Dev Workspace under `/home/dev/projects` and its persistent home      |
| Selected original Nextcloud or FileBrowser files                            | `/projects-shared` in Dev Workspace, backed by that provider          |
| Podman images, containers and named volumes                                 | Dev Workspace's separate engine storage                               |
| A terminal after reopening a Dev Container                                  | The selected development container                                    |
| A Web Preview opened on your computer                                       | Your browser reaches the application through StartOS                  |

Open **Extensions** in the remote window to check the **Local - Installed** and **SSH: dev-workspace** groups. Let each extension use its supported installation location; language tools may need installation on the SSH host. Do not force every extension into the desktop. Account sign-in, coding agents, Git authentication and server administration have separate credentials and requirements. [Remote SSH extension placement](https://code.visualstudio.com/docs/remote/ssh#_managing-extensions).

Use **Developer: Show Running Extensions** to inspect execution placement after activation. Native checks showed Remote SSH and Dev Containers in the desktop extension host, with Codex and Git in the SSH extension host. An extension installed remotely may remain inactive in Restricted Mode. This placement check does not establish coding-agent account access or a completed agent workflow.

Before starting a build, use **Terminal > New Terminal** and check `whoami`, `pwd`, and `command -v node podman docker start-cli`. The normal Remote SSH account is `dev`; an explicitly local terminal reports `abc` and displays a local-machine notice. These commands establish the current environment; a successful project or container command is still needed to verify that workflow. Opening another folder does not require a second Podman installation.

## Using the desktop

VS Code opens automatically when the companion starts. After pairing, it reopens the selected remote folder once any keyring prompt is unlocked. Editor preferences and installed extensions persist across companion restarts. Workspace Trust is still your choice; trust only folders whose code you intend to run.

Use VS Code's **Explorer**, **Terminal**, and built-in **Browser** for development. This companion has no separate browser or file manager. Standalone desktop terminals and sudo are disabled. Window controls and the streaming sidebar remain available, and everyone with desktop access shares the same session.

Revision **0.1.0:1** disables the streaming service's file-upload, file-download and file-browsing endpoints. Use VS Code or your project's existing file tools for files. Clipboard text and images are separate controls in the streaming sidebar. The initial **0.1.0:0** revision did not enforce the intended file-transfer restriction.

Closing your browser disconnects your view without stopping the desktop. If you close the last VS Code window, restart this companion from StartOS to reopen it. Save work before restarting. The Desktop Stream check turns green when the web endpoint accepts the desktop credentials and the streaming service answers its reconnect probe. External TLS routing and the editor can still be starting. If reconnection fails just after a restart, wait briefly and reopen the StartOS interface.

Run **Workspace Connection Status** if a connection fails. A missing address retains your key and trusted host identity; start Dev Workspace and try again. A changed host fingerprint requires verification before reconnecting. Never accept an unfamiliar replacement simply to dismiss an error.

**Forget Workspace Connection** disables the local target and retains its key. To revoke future logins, also remove that public fingerprint through Dev Workspace's **Remove SSH Key**. **Rotate Workspace Key** creates a replacement: authorize its new public key, remove the old fingerprint in Dev Workspace, then connect again. These actions restart this desktop. Existing authenticated sessions require separate termination.

### When typing feels slow

Try resizing the browser window to about 1100 by 760 pixels. In a Brave typing test on x86 StartOS 0.4.2, that size reduced the time between a keystroke and its visible response compared with a 1440 by 1000 window. The smaller desktop also used less streaming-process CPU. Enlarge the window again whenever you need the space. Both sizes use the existing software renderer.

## Dev Containers

Enable Podman in Dev Workspace and install Microsoft's **Dev Containers** extension in this desktop. Open a local-storage project through Remote SSH, add its `.devcontainer/devcontainer.json`, and run **Dev Containers: Reopen in Container**. The workspace supplies the `docker` compatibility command and `podman-compose`, so the tested Node/Compose workflow needs no container engine in this desktop or on your computer.

Use **Dev Containers: Rebuild Container** after image changes. Keep project data in bind mounts or named volumes so it survives rebuilding. The tested rootless configuration uses `remoteUser: "root"` inside the container and preserves UID 1000 ownership on workspace files; other container-user configurations need their own ownership checks.

The **Ports** panel forwards application ports to this desktop's localhost. Open that address using VS Code's built-in Browser. A Web Preview interface provides an address for your own computer's browser. Applications may need restarting after a rebuild or reopen.

## Open a running application

When your Dev Workspace version provides **Web Previews**, use this flow from your own computer:

1. Start the application in the remote terminal or its local-storage container project. Note the port published in Dev Workspace, for example `3000` for Rails or `5173` for Vite.
2. Complete **Set Web Preview Password** once in Dev Workspace and retain that access credential separately from the desktop password.
3. Run **Add Web Preview**, entering only its **Name**, **Application Port**, and **Duration**.
4. Open the returned StartOS interface in your computer's browser and sign in with the preview credential. Use its assigned HTTPS address, including any external port. The application port and external port can differ.
5. Use **List Web Previews** for readiness and expiry, **Extend Web Preview** for more time, or **Remove Web Preview** to close that browser route.

An application that is still starting can have a preview address without being ready. Expiry or removal closes preview access while the application continues running. The desktop password, preview password and an application's own login are separate. Keep public exposure under the preview's StartOS interface controls. Follow Dev Workspace's instructions for Rails host/CSRF settings, Vite host/HMR settings and container port publication.

To view the application inside the streamed desktop, open VS Code’s **Ports** panel and copy the forwarded address into VS Code’s built-in Browser. Read the forwarded address from the panel because its local port may differ from the application port. In this streamed desktop, `localhost` belongs to the desktop client; entering that address in your computer's browser reaches your computer instead. [Remote SSH port forwarding](https://code.visualstudio.com/docs/remote/ssh#_forwarding-a-port-creating-ssh-tunnel).

## Building StartOS packages

Use the Remote SSH terminal and Dev Workspace's local project storage. Create a StartOS packaging workspace, place the package repository inside it, then run its dependency installation and build commands, commonly `npm ci` and `make x86`. The workspace provides `start-cli` and selects Podman for packaging. S9PK signing uses the packaging workspace's `.startos/build.key.pem`; the CLI's server-login identity is separate.

The resulting archive stays on the server and can be inspected with `start-cli s9pk inspect <package.s9pk> manifest`. A disposable x86_64 package has passed this workflow from the streamed terminal. Building does not install or publish it. Use Dev Workspace's separate package-manager actions when you intend to review and install an artifact.

## Access and recovery

Run **Set Desktop Password** again if you need a new access password. It restarts this desktop, so save your work first. Use a browser that trusts the server's HTTPS certificate.

Save files before stopping the desktop. A backup contains stored desktop data, not unsaved buffers or running processes. Back up Dev Workspace and your file providers separately for project recovery.

The companion backup declaration includes its access credential, editor versions, preferences, extensions, keyring, pairing key and pinned host. Recover the editor database and its matching keyring from the same companion backup, then use **Unlock Keyring** with the password that applied when that backup was taken. Testing has verified credential retrieval after a companion restart. Credential retrieval after a full StartOS restore remains unverified. If restoring a copy while the original companion still exists, keep the copy disconnected until you deliberately choose whether it retains or rotates the pairing identity. Two copies of a pairing key represent the same SSH authorization.

| Symptom                                               | Next step                                                                                                                                                          |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Browser reports an untrusted certificate              | Trust the server CA on that client and reopen the current StartOS interface                                                                                        |
| Password challenge repeats                            | Use username `desktop` and the current generated desktop password; rotate it through the action if needed                                                          |
| Desktop Stream is healthy but the editor is not visible | Check **Keyring Status**, run **Unlock Keyring** if locked, then reconnect to see the editor                                               |
| No workspace address or SSH connection                | Start Dev Workspace, run **Workspace Connection Status**, and check that its authorized public key still matches the companion key                                 |
| Host fingerprint changed                              | Compare it with Dev Workspace's current **Connection Information** before using **Connect to Dev Workspace** again                                                 |
| Remote bootstrap fails                                | Inspect **Output → Remote - SSH**; retain the tested `remote.SSH.useExecServer=false` and `remote.SSH.localServerDownload=always` fallback when needed             |
| Podman is unavailable                                 | Confirm the window is remote and Docker is enabled in Dev Workspace; open container projects from local project storage                                            |
| Shared folder is missing or read-only                 | Check the provider selection, account and health in Dev Workspace; do not substitute the desktop's local folder                                                    |
| Editor installation fails                             | Read the action error and check Internet access and free space; retained-editor recovery requires companion revision `0.1.0:2` and its remaining native validation |

## Resource expectations

The editor installer requires at least 2.5 GiB free in its storage filesystem. This is an installation check, not a total server capacity recommendation. Keep additional space for the Selkies image, retained editor versions, extensions and backups. Dev Workspace separately stores project dependencies, container layers, databases and package-build scratch files. Cleaning Podman does not remove the companion's editor versions or provider cache.

Native x86 measurements of companion `0.1.0:1` with VS Code 1.145.3 and one Chromium session at 1440x1000 recorded the following. The desktop used software rendering while Rails, frontends and database/mail containers ran in Dev Workspace.

| Companion measurement                           | Observed value                                                          |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| Idle proportional RAM                           | About 1.28 GiB                                                          |
| Peak proportional RAM during concurrent editing | About 1.33 GiB, plus separate project and container memory              |
| Average CPU during concurrent editing           | About 63% of one logical CPU                                            |
| Peak sampled CPU during concurrent editing      | About 229% of one logical CPU, equivalent to 2.29 cores                 |
| Persistent editor, extensions and configuration | About 1.08 GiB; no net allocated growth during the short sample windows |

The separate disposable project workloads occupied about 1.29 GiB, including dependencies, runtimes, caches, container images and database files. Their sizes are examples, not storage allowances for your projects. Companion image storage, retained editor releases and backups need additional capacity.

All eleven measured editor saves matched the remote file bytes. With both application stacks running, independent verification observed each save within about 470 to 598 ms; that timing includes the verification command and network overhead. Closing the browser, reconnecting and saving again also passed, as did 2,541 application responses.

These measurements cover one bounded workload on a server with 12 logical CPUs. They do not establish minimum hardware, capacity for larger displays or additional viewers, or enforced CPU/RAM quotas. Streaming, extensions and builds can increase resource use. Use server resource monitoring to leave headroom above the observed desktop cost and your project requirements; cleaning Podman does not reduce desktop memory or remove installed editor versions.

## Candidate limitations

The native validation record uses the following combination. These are tested versions, not a claim that every later release or browser works.

| Component                                           | Tested configuration                                      |
| --------------------------------------------------- | --------------------------------------------------------- |
| StartOS and processor                               | StartOS 0.4.2 on x86_64                                   |
| Companion installed for latest native access checks | `0.1.0:4`                                                 |
| Desktop editor                                      | Microsoft VS Code 1.145.3                                 |
| Remote SSH                                          | 0.128.0                                                   |
| Dev Containers                                      | 0.473.0                                                   |
| Browsers                                            | Playwright Chromium 159.0.8154.6 and Firefox 159.0          |

Native x86 desktop operation, pairing, a Node/Compose Dev Containers workflow and companion restart have passed. Chromium and Firefox checks include saved edits, clipboard text, resize, reconnect and streams observed for about ten minutes. Those observations do not guarantee indefinite idle connections. On x86, revision `0.1.0:2` passed installed Chromium checks for left and right Command, continued typing and saving after reconnect. On x86 revision `0.1.0:4`, Firefox 159 on macOS saved the complete typed text with Ctrl, left Command, and right Command, and saved another edit after reconnecting. Safari/WebKit remains unverified.

Revision `0.1.0:4` passed installed x86 checks for keyring startup, unlock through StartOS, editor launch, authenticated streaming and reconnect after restart. Full native ARM StartOS operation, extension-account sign-in and backup/restore still require acceptance.

Use your application's Web Preview interface to open it in your own browser. A localhost address inside the streamed desktop refers to that desktop's environment.

This companion streams the Linux desktop application. [code-server](https://coder.com/docs/code-server) and [OpenVSCode Server](https://github.com/gitpod-io/openvscode-server/blob/main/README.md) provide editors served directly to a browser. They are separate alternatives with their own setup and extension support; neither is installed by this companion or substituted for its desktop VS Code workflow.
