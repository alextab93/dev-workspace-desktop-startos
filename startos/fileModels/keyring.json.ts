import { FileHelper, z } from '@start9labs/start-sdk'
import { sdk } from '../sdk'

export const keyringState = FileHelper.json(
  {
    base: sdk.volumes.config,
    subpath: './.local/share/dev-workspace-desktop/keyring-control/status.json',
  },
  z.object({ state: z.enum(['not-created', 'locked', 'unlocked']) }),
)
