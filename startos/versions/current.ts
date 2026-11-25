import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.1.0:11',
  releaseNotes: {
    en_US: 'Ensure the desktop user can read startup helpers on every build.',
    es_ES:
      'Garantiza que el usuario del escritorio pueda leer los archivos de inicio.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
