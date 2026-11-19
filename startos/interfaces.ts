import { sdk } from './sdk'
import { i18n } from './i18n'
import { desktopSettings } from './fileModels/desktop.json'
import {
  desktopHostId,
  desktopUsername,
  editorSetupState,
  uiPort,
} from './utils'

export const setInterfaces = sdk.setupInterfaces(async ({ effects }) => {
  const settings = await desktopSettings.read().const(effects)
  if (
    !settings?.password ||
    editorSetupState(settings.editorVersion) === 'required'
  )
    return []
  const host = sdk.MultiHost.of(effects, desktopHostId)
  const origin = await host.bindPort(uiPort, {
    protocol: 'http',
    preferredExternalPort: uiPort,
    addSsl: { preferredExternalPort: 3001, alpn: ['http/1.1'] },
    proxy: {
      auth: {
        type: 'basic',
        credentials: [
          { username: desktopUsername, password: settings.password },
        ],
        realm: 'Dev Workspace Desktop',
      },
    },
  })
  const desktop = sdk.createInterface(effects, {
    id: desktopHostId,
    name: i18n('Desktop VS Code'),
    description: i18n(
      'Open the desktop editor and connect to Dev Workspace through Remote SSH.',
    ),
    type: 'ui',
    masked: false,
    schemeOverride: null,
    username: null,
    path: '',
    query: {},
  })
  return [await origin.export([desktop])]
})
