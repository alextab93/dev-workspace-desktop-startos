import { sdk } from '../sdk'
import { i18n } from '../i18n'
import { workspaceAddress } from '../utils'
import {
  restartDesktopConnection,
  runWorkspaceCommand,
  type WorkspaceConnection,
} from '../workspace'

function connectionDetails(connection: WorkspaceConnection) {
  const values = [
    [i18n('Public Key'), connection.publicKey],
    [i18n('Key Fingerprint'), connection.keyFingerprint],
    [i18n('Previous Key Fingerprint'), connection.previousFingerprint],
    [i18n('Workspace Host Fingerprint'), connection.hostFingerprint],
    [i18n('Project Folder'), connection.folder],
  ]
  return {
    type: 'group' as const,
    value: values
      .filter(([, value]) => value !== undefined)
      .map(([name, value]) => ({
        type: 'single' as const,
        name: name!,
        description: null,
        value: value!,
        masked: false,
        copyable: true,
        qr: false,
        launchable: false,
      })),
  }
}

export const prepareWorkspaceKey = sdk.Action.withoutInput(
  'prepare-workspace-key',
  async () => ({
    name: i18n('Prepare Workspace Key'),
    description: i18n(
      'Create or show this desktop public key for Dev Workspace.',
    ),
    warning: null,
    allowedStatuses: 'any',
    group: i18n('Workspace Connection'),
    visibility: 'enabled',
  }),
  async ({ effects }) => ({
    version: '1',
    title: i18n('Workspace Public Key'),
    message: i18n(
      'Add this public key in Dev Workspace using Add SSH Key, then run Connect to Dev Workspace. Keep the private key in this desktop.',
    ),
    result: connectionDetails(await runWorkspaceCommand(effects, ['key'])),
  }),
)

export const connectWorkspace = sdk.Action.withInput(
  'connect-workspace',
  async () => ({
    name: i18n('Connect to Dev Workspace'),
    description: i18n(
      'Verify the workspace identity and open your remote project.',
    ),
    warning: i18n(
      'Save your desktop work. A successful connection restarts this desktop; Dev Workspace continues running.',
    ),
    allowedStatuses: 'any',
    group: i18n('Workspace Connection'),
    visibility: 'enabled',
  }),
  sdk.InputSpec.of({
    fingerprint: sdk.Value.text({
      name: i18n('Workspace Host Fingerprint'),
      description: i18n(
        'Copy the Ed25519 SHA256 fingerprint from Dev Workspace Connection Information.',
      ),
      required: true,
      default: null,
      masked: false,
    }),
    folder: sdk.Value.select({
      name: i18n('Project Folder'),
      values: {
        '/home/dev/projects': i18n('Local Projects'),
        '/projects-shared': i18n('Shared Projects'),
      },
      default: '/home/dev/projects',
    }),
  }),
  async () => ({}),
  async ({ effects, input }) => {
    const endpoint = await workspaceAddress(effects).once()
    if (!endpoint)
      throw new Error(
        i18n(
          'Dev Workspace has no available SSH address. Install and start it, then try again.',
        ),
      )
    const connection = await runWorkspaceCommand(effects, [
      'pair',
      '--endpoint',
      endpoint,
      '--fingerprint',
      input.fingerprint,
      '--folder',
      input.folder,
    ])
    await restartDesktopConnection(effects)
    return {
      version: '1',
      title: i18n('Workspace Connected'),
      message: i18n(
        'SSH access and the selected folder were verified. Install Remote SSH in the desktop editor, then open the Dev Workspace target.',
      ),
      result: connectionDetails(connection),
    }
  },
)

export const workspaceStatus = sdk.Action.withoutInput(
  'workspace-connection-status',
  async () => ({
    name: i18n('Workspace Connection Status'),
    description: i18n(
      'Check the current workspace address, host identity and SSH access.',
    ),
    warning: null,
    allowedStatuses: 'any',
    group: i18n('Workspace Connection'),
    visibility: 'enabled',
  }),
  async ({ effects }) => {
    const endpoint = await workspaceAddress(effects).once()
    let connection = await runWorkspaceCommand(effects, [
      'refresh',
      '--endpoint',
      endpoint ?? '',
    ])
    if (connection.state === 'paired')
      connection = await runWorkspaceCommand(effects, ['check'])
    return {
      version: '1',
      title: i18n('Workspace Connection Status'),
      message: connection.verified
        ? i18n(
            'The pinned workspace identity, SSH access and project folder are verified.',
          )
        : connection.state === 'offline'
          ? i18n(
              'The workspace address is unavailable. The saved key and trusted host identity are retained.',
            )
          : i18n(
              'This desktop is not paired. Prepare its key, authorize it in Dev Workspace, then connect.',
            ),
      result: connectionDetails(connection),
    }
  },
)

export const forgetWorkspace = sdk.Action.withoutInput(
  'forget-workspace',
  async () => ({
    name: i18n('Forget Workspace Connection'),
    description: i18n(
      'Remove the desktop connection while retaining its dedicated key.',
    ),
    warning: i18n(
      'Restarts this desktop. Remove its public key in Dev Workspace to revoke future logins; existing sessions need separate termination.',
    ),
    allowedStatuses: 'any',
    group: i18n('Workspace Connection'),
    visibility: 'enabled',
  }),
  async ({ effects }) => {
    const connection = await runWorkspaceCommand(effects, ['forget'])
    await restartDesktopConnection(effects)
    return {
      version: '1',
      title: i18n('Workspace Connection Removed'),
      message: i18n(
        'The desktop target is disabled. Use Remove SSH Key in Dev Workspace with the shown fingerprint to revoke this key.',
      ),
      result: connectionDetails(connection),
    }
  },
)

export const rotateWorkspaceKey = sdk.Action.withoutInput(
  'rotate-workspace-key',
  async () => ({
    name: i18n('Rotate Workspace Key'),
    description: i18n(
      'Replace this desktop key and require a new workspace authorization.',
    ),
    warning: i18n(
      'Restarts this desktop and removes its connection. Authorize the new public key and remove the previous fingerprint in Dev Workspace.',
    ),
    allowedStatuses: 'any',
    group: i18n('Workspace Connection'),
    visibility: 'enabled',
  }),
  async ({ effects }) => {
    const connection = await runWorkspaceCommand(effects, ['rotate'])
    await restartDesktopConnection(effects)
    return {
      version: '1',
      title: i18n('Workspace Key Replaced'),
      message: i18n(
        'Add the new public key, remove the previous key in Dev Workspace, then connect again. Existing sessions require separate termination.',
      ),
      result: connectionDetails(connection),
    }
  },
)
