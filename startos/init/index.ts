import { sdk } from '../sdk'
import { dependencies } from '../dependencies'
import { setInterfaces } from '../interfaces'
import { versionGraph } from '../versions'
import { actions } from '../actions'
import { restoreInit } from '../backups'
import { initializeDesktop, watchDesktopSetup } from './setup'
import { watchKeyring } from './keyring'

export const init = sdk.setupInit(
  restoreInit,
  versionGraph,
  initializeDesktop,
  setInterfaces,
  actions,
  dependencies,
  watchDesktopSetup,
  watchKeyring,
)

export const uninit = sdk.setupUninit(versionGraph)
