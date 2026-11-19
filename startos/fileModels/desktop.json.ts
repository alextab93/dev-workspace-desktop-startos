import { FileHelper, z } from '@start9labs/start-sdk'
import { sdk } from '../sdk'

export const desktopSettings = FileHelper.json(
  { base: sdk.volumes.main, subpath: './desktop.json' },
  z.looseObject({
    password: z.string().min(32).nullable().catch(null),
    editorVersion: z.string().nullable().catch(null),
    connectionRevision: z.number().int().nonnegative().catch(0),
  }),
)
