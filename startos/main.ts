import { desktopStreamReady } from './desktopStream'
import { i18n } from './i18n'
import { sdk } from './sdk'
import {
  desktopMounts,
  desktopUsername,
  editorSetupState,
  uiPort,
  workspaceAddress,
  workspaceHelper,
} from './utils'
import { desktopSettings } from './fileModels/desktop.json'

export const main = sdk.setupMain(async ({ effects }) => {
  const settings = await desktopSettings.read().const(effects)
  if (
    !settings?.password ||
    editorSetupState(settings.editorVersion) === 'required'
  )
    throw new Error(i18n('Complete desktop setup before starting the service.'))
  const password = settings.password
  const endpoint = await workspaceAddress(effects).const()
  const desktop = sdk.SubContainer.of(
    effects,
    { imageId: 'desktop' },
    desktopMounts(),
    'desktop',
  )
  const connection = { endpoint, revision: settings.connectionRevision }
  return sdk.Daemons.of(effects)
    .addOneshot('workspace-target', {
      subcontainer: desktop,
      uses: connection,
      exec: {
        fn: async (container) => {
          await container.execFail(['chown', 'abc:abc', '/config'], {
            user: 'root',
          })
          await container.execFail(
            [
              'python3',
              workspaceHelper,
              'refresh',
              '--endpoint',
              endpoint ?? '',
            ],
            { user: 'abc' },
          )
          return null
        },
      },
      requires: [],
    })
    .addDaemon('desktop', {
      subcontainer: desktop,
      uses: connection,
      exec: {
        command: sdk.useEntrypoint(),
        runAsInit: true,
        env: {
          PUID: '911',
          PGID: '911',
          CUSTOM_USER: desktopUsername,
          PASSWORD: password,
        },
      },
      ready: {
        display: i18n('Desktop Stream'),
        fn: async () =>
          (await desktopStreamReady(uiPort, desktopUsername, password))
            ? {
                result: 'success' as const,
                message: i18n('The desktop stream is accepting connections.'),
              }
            : {
                result: 'failure' as const,
                message: i18n('The desktop stream is unavailable.'),
              },
      },
      requires: ['workspace-target'],
    })
    .addDaemon('keyring', {
      subcontainer: desktop,
      uses: connection,
      exec: {
        command: [
          'python3',
          '-B',
          '/usr/local/lib/dev-workspace-desktop/keyring.py',
          'supervise',
        ],
        user: 'abc',
        env: { HOME: '/config', XDG_DATA_HOME: '/config/.local/share' },
      },
      ready: {
        display: i18n('Desktop Keyring'),
        fn: async () => {
          try {
            const result = await desktop.execFail(
              [
                'python3',
                '-B',
                '/usr/local/lib/dev-workspace-desktop/keyring.py',
                'request',
              ],
              {
                user: 'abc',
                input: JSON.stringify({ operation: 'status' }),
                timeout: 70000,
              },
            )
            const current = JSON.parse(String(result.stdout))
            if (!['not-created', 'locked', 'unlocked'].includes(current.state))
              throw new Error('Invalid keyring status')
            return {
              result: 'success' as const,
              message:
                current.state === 'unlocked'
                  ? i18n(
                      'The keyring is unlocked. Desktop VS Code can use its saved credentials.',
                    )
                  : current.state === 'locked'
                    ? i18n(
                        'The keyring is locked. Use Unlock Keyring to open the editor.',
                      )
                    : i18n(
                        'No default keyring exists. Use Set Keyring Password to create it.',
                      ),
            }
          } catch {
            return {
              result: 'failure' as const,
              message: i18n(
                'Keyring service is unavailable. Restart this desktop and try again.',
              ),
            }
          }
        },
      },
      requires: ['desktop'],
    })
})
