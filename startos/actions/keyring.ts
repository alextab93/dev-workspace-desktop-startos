import { type T, z } from '@start9labs/start-sdk'
import { sdk } from '../sdk'
import { i18n } from '../i18n'
import { desktopMounts } from '../utils'

const state = z.object({
  state: z.enum(['not-created', 'locked', 'unlocked']),
})

async function command(effects: T.Effects, input: Record<string, unknown>) {
  return sdk.SubContainer.withTemp(
    effects,
    { imageId: 'desktop' },
    desktopMounts(),
    'keyring-control',
    async (container) => {
      const result = await container.exec(
        [
          'python3',
          '-B',
          '/usr/local/lib/dev-workspace-desktop/keyring.py',
          'request',
        ],
        { user: 'abc', input: JSON.stringify(input), timeout: 70000 },
      )
      if (result.exitCode !== 0)
        throw new Error(
          i18n(
            'Keyring access failed. Check the password and confirm the desktop is running. Saved credentials are retained.',
          ),
        )
      return state.parse(JSON.parse(String(result.stdout)))
    },
  )
}

function result(value: z.infer<typeof state>) {
  return {
    version: '1' as const,
    title: i18n('Desktop Keyring'),
    message:
      value.state === 'unlocked'
        ? i18n(
            'The keyring is unlocked. Desktop VS Code can use its saved credentials.',
          )
        : value.state === 'locked'
          ? i18n(
              'The keyring is locked. Use Unlock Keyring to open the editor.',
            )
          : i18n(
              'No default keyring exists. Use Set Keyring Password to create it.',
            ),
    result: null,
  }
}

export const setKeyringPassword = sdk.Action.withInput(
  'set-keyring-password',
  async () => ({
    name: i18n('Set Keyring Password'),
    description: i18n(
      'Create or change the password protecting saved editor credentials.',
    ),
    warning: i18n(
      'Changing an existing keyring requires its current password. Saved credentials are preserved. This is separate from the desktop browser password.',
    ),
    allowedStatuses: 'only-running',
    group: i18n('Desktop Keyring'),
    visibility: 'enabled',
  }),
  sdk.InputSpec.of({
    currentPassword: sdk.Value.text({
      name: i18n('Current Keyring Password'),
      description: i18n('Leave empty only when creating your first keyring.'),
      required: false,
      default: null,
      masked: true,
    }),
    password: sdk.Value.text({
      name: i18n('New Keyring Password'),
      description: i18n(
        'Choose at least 12 characters. Keep it for unlocking after a desktop restart.',
      ),
      required: true,
      default: null,
      masked: true,
    }),
    confirmation: sdk.Value.text({
      name: i18n('Confirm Keyring Password'),
      description: null,
      required: true,
      default: null,
      masked: true,
    }),
  }),
  async () => ({}),
  async ({ effects, input }) => {
    if (input.password !== input.confirmation)
      throw new Error(i18n('The new keyring passwords do not match.'))
    if (input.password.length < 12)
      throw new Error(
        i18n('Choose a keyring password of at least 12 characters.'),
      )
    return result(await command(effects, { operation: 'set', ...input }))
  },
)

export const unlockKeyring = sdk.Action.withInput(
  'unlock-keyring',
  async () => ({
    name: i18n('Unlock Keyring'),
    description: i18n(
      'Unlock saved editor credentials for this desktop session.',
    ),
    warning: null,
    allowedStatuses: 'only-running',
    group: i18n('Desktop Keyring'),
    visibility: 'enabled',
  }),
  sdk.InputSpec.of({
    password: sdk.Value.text({
      name: i18n('Keyring Password'),
      description: i18n(
        'Use your keyring password, which can differ from the desktop browser password.',
      ),
      required: true,
      default: null,
      masked: true,
    }),
  }),
  async () => ({}),
  async ({ effects, input }) =>
    result(await command(effects, { operation: 'unlock', ...input })),
)

export const keyringStatus = sdk.Action.withoutInput(
  'keyring-status',
  async () => ({
    name: i18n('Keyring Status'),
    description: i18n(
      'Check whether the desktop keyring needs setup or unlocking.',
    ),
    warning: null,
    allowedStatuses: 'only-running',
    group: i18n('Desktop Keyring'),
    visibility: 'enabled',
  }),
  async ({ effects }) =>
    result(await command(effects, { operation: 'status' })),
)
