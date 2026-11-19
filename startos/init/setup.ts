import * as fs from 'node:fs/promises'
import path from 'node:path'
import { sdk } from '../sdk'
import { i18n } from '../i18n'
import { desktopSettings } from '../fileModels/desktop.json'
import { installEditor, setPassword } from '../actions/setup'
import { editorSetupState } from '../utils'

export const initializeDesktop = sdk.setupOnInit(async (effects) => {
  await fs.mkdir(path.dirname(desktopSettings.path), {
    recursive: true,
    mode: 0o700,
  })
  await desktopSettings.update(
    effects,
    (current) =>
      current ?? { password: null, editorVersion: null, connectionRevision: 0 },
  )
})

export const watchDesktopSetup = sdk.setupOnInit(async (effects) => {
  const settings = await desktopSettings.read().const(effects)
  if (settings?.password) {
    await sdk.action.clearTask(
      effects,
      'dev-workspace-desktop:set-desktop-password',
    )
  } else {
    await sdk.action.createOwnTask(effects, setPassword, 'critical', {
      reason: i18n('Set a password before opening the desktop.'),
    })
  }
  const editorState = editorSetupState(settings?.editorVersion)
  if (editorState !== 'required') {
    await sdk.action.clearTask(effects, 'dev-workspace-desktop:install-editor')
  }
  if (editorState !== 'update') {
    await sdk.action.clearTask(effects, 'dev-workspace-desktop:update-editor')
  }
  if (editorState === 'required') {
    await sdk.action.createOwnTask(effects, installEditor, 'critical', {
      reason: i18n(
        'Install the selected desktop editor before starting the service.',
      ),
    })
  } else if (editorState === 'update') {
    await sdk.action.createOwnTask(effects, installEditor, 'important', {
      replayId: 'dev-workspace-desktop:update-editor',
      reason: i18n(
        'An editor update is available. The installed editor remains usable until you update.',
      ),
    })
  }
})
