import { sdk } from '../sdk'
import { i18n } from '../i18n'
import { keyringState } from '../fileModels/keyring.json'
import { setKeyringPassword, unlockKeyring } from '../actions/keyring'

export const watchKeyring = sdk.setupOnInit(async (effects) => {
  const current = await keyringState.read().const(effects)
  if (current?.state === 'not-created') {
    await sdk.action.createOwnTask(effects, setKeyringPassword, 'important', {
      reason: i18n('Create your keyring password to open the desktop editor.'),
    })
  } else {
    await sdk.action.clearTask(
      effects,
      'dev-workspace-desktop:set-keyring-password',
    )
  }
  if (current?.state === 'locked') {
    await sdk.action.createOwnTask(effects, unlockKeyring, 'important', {
      reason: i18n(
        'Unlock the keyring after a desktop restart to open the editor.',
      ),
    })
  } else {
    await sdk.action.clearTask(effects, 'dev-workspace-desktop:unlock-keyring')
  }
})
