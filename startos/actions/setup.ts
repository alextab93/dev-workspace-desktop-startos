import { utils } from '@start9labs/start-sdk'
import { sdk } from '../sdk'
import { i18n } from '../i18n'
import { desktopSettings } from '../fileModels/desktop.json'
import { desktopMounts, editorVersion, desktopUsername } from '../utils'

export const setPassword = sdk.Action.withoutInput(
  'set-desktop-password',
  async ({ effects }) => ({
    name: i18n('Set Desktop Password'),
    description: i18n('Generate a password for opening the desktop interface.'),
    warning: (await desktopSettings
      .read((state) => state.password)
      .const(effects))
      ? i18n(
          'Replaces the current password and restarts this desktop. Dev Workspace continues running.',
        )
      : null,
    allowedStatuses: 'any',
    group: null,
    visibility: 'enabled',
  }),
  async ({ effects }) => {
    const password = utils.getDefaultString({ charset: 'a-z,A-Z,0-9', len: 40 })
    await desktopSettings.update(effects, (current) => ({
      ...current,
      editorVersion: current?.editorVersion ?? null,
      connectionRevision: current?.connectionRevision ?? 0,
      password,
    }))
    return {
      version: '1',
      title: i18n('Desktop Access'),
      message: i18n('Save the password before closing this result.'),
      result: {
        type: 'group',
        value: [
          {
            type: 'single',
            name: i18n('Username'),
            description: null,
            value: desktopUsername,
            masked: false,
            copyable: true,
            qr: false,
            launchable: false,
          },
          {
            type: 'single',
            name: i18n('Password'),
            description: null,
            value: password,
            masked: true,
            copyable: true,
            qr: false,
            launchable: false,
          },
        ],
      },
    }
  },
)

export const installEditor = sdk.Action.withoutInput(
  'install-editor',
  async () => ({
    name: i18n('Install Desktop VS Code'),
    description: i18n(
      'Download and verify the selected Microsoft editor into persistent desktop storage.',
    ),
    warning: i18n(
      'Downloads desktop VS Code from Microsoft for private development. Microsoft product terms apply: https://code.visualstudio.com/license. Extensions have separate terms. Requires at least 2.5 GiB of free storage.',
    ),
    allowedStatuses: 'only-stopped',
    group: null,
    visibility: 'enabled',
  }),
  async ({ effects }) => {
    await sdk.SubContainer.withTemp(
      effects,
      { imageId: 'desktop' },
      desktopMounts(),
      'editor-installer',
      async (container) => {
        await container.execFail(['chown', 'abc:abc', '/config'], {
          user: 'root',
        })
        await container.execFail(
          ['python3', '/usr/local/lib/dev-workspace-desktop/install-editor.py'],
          { user: 'abc', timeout: 240000 },
        )
      },
    )
    await desktopSettings.update(effects, (current) => ({
      ...current,
      password: current?.password ?? null,
      connectionRevision: current?.connectionRevision ?? 0,
      editorVersion,
    }))
    return {
      version: '1',
      title: i18n('Editor Installed'),
      message: i18n(
        'The selected editor is installed. Set a desktop password if needed, then start the service.',
      ),
      result: {
        type: 'single',
        value: editorVersion,
        masked: false,
        copyable: true,
        qr: false,
        launchable: false,
      },
    }
  },
)
