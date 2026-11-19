import { sdk } from '../sdk'
import { installEditor, setPassword } from './setup'
import { keyringStatus, setKeyringPassword, unlockKeyring } from './keyring'
import {
  connectWorkspace,
  forgetWorkspace,
  prepareWorkspaceKey,
  rotateWorkspaceKey,
  workspaceStatus,
} from './workspace'

export const actions = sdk.Actions.of()
  .addAction(installEditor)
  .addAction(setPassword)
  .addAction(setKeyringPassword)
  .addAction(unlockKeyring)
  .addAction(keyringStatus)
  .addAction(prepareWorkspaceKey)
  .addAction(connectWorkspace)
  .addAction(workspaceStatus)
  .addAction(forgetWorkspace)
  .addAction(rotateWorkspaceKey)
