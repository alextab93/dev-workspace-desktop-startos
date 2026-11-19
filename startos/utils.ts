import { sdk } from './sdk'
import { type T } from '@start9labs/start-sdk'
import releases from '../assets/editor-releases.json'

export const uiPort = 3000
export const desktopHostId = 'desktop'
export const desktopUsername = 'desktop'
export const editorVersion = releases.x64.version
export const workspacePackageId = 'dev-workspace'
export const workspaceMinimumVersion = '>=0.5.0:1'
export const workspaceHelper =
  '/usr/local/lib/dev-workspace-desktop/workspace-connection.py'

export const editorSetupState = (
  installedVersion: string | null | undefined,
) => {
  if (
    !installedVersion ||
    installedVersion.trim() !== installedVersion ||
    !/^\d+\.\d+\.\d+$/.test(installedVersion)
  )
    return 'required'
  return installedVersion === editorVersion ? 'ready' : 'update'
}

export const workspaceAddress = (effects: T.Effects) =>
  sdk.host.getBridgeAddress(effects, {
    packageId: workspacePackageId,
    hostId: 'ssh',
    internalPort: 2222,
  })

export const desktopMounts = () =>
  sdk.Mounts.of().mountVolume({
    volumeId: 'config',
    subpath: null,
    mountpoint: '/config',
    readonly: false,
  })
