import { type T, z } from '@start9labs/start-sdk'
import { sdk } from './sdk'
import { desktopSettings } from './fileModels/desktop.json'
import { desktopMounts, workspaceHelper } from './utils'

const connectionResult = z.looseObject({
  state: z.enum(['unpaired', 'paired', 'offline']).optional(),
  alias: z.string().optional(),
  publicKey: z.string().optional(),
  keyFingerprint: z.string().optional(),
  previousFingerprint: z.string().optional(),
  hostFingerprint: z.string().optional(),
  folder: z.string().optional(),
  verified: z.boolean().optional(),
  endpoint: z
    .looseObject({ host: z.string(), port: z.number().int() })
    .nullable()
    .optional(),
})

export type WorkspaceConnection = z.infer<typeof connectionResult>

export const runWorkspaceCommand = (effects: T.Effects, args: string[]) =>
  sdk.SubContainer.withTemp(
    effects,
    { imageId: 'desktop' },
    desktopMounts(),
    'workspace-connection',
    async (container) => {
      await container.execFail(['chown', 'abc:abc', '/config'], {
        user: 'root',
      })
      const result = await container.execFail(
        ['python3', workspaceHelper, ...args],
        { user: 'abc', timeout: 30000 },
      )
      return connectionResult.parse(JSON.parse(String(result.stdout)))
    },
  )

export const restartDesktopConnection = (effects: T.Effects) =>
  desktopSettings.update(effects, (current) => ({
    ...current,
    password: current?.password ?? null,
    editorVersion: current?.editorVersion ?? null,
    connectionRevision: (current?.connectionRevision ?? 0) + 1,
  }))
