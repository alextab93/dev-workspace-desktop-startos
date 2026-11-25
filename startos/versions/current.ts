import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.1.0:10',
  releaseNotes: {
    en_US: 'Document how browser viewport size affects the streamed desktop.',
    es_ES:
      'Documenta cómo el tamaño de la ventana del navegador afecta al escritorio remoto.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
