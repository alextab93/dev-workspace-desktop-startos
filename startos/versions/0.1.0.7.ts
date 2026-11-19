import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const v0_1_0_7 = VersionInfo.of({
  version: '0.1.0:7',
  releaseNotes: {
    en_US:
      'Preserve the latest desktop and editor settings in repeated backups.',
    es_ES:
      'Conserva la configuración más reciente del escritorio y del editor en copias de seguridad sucesivas.',
    de_DE:
      'Bewahrt die aktuellen Desktop- und Editoreinstellungen bei wiederholten Sicherungen.',
    pl_PL:
      'Zachowuje najnowsze ustawienia pulpitu i edytora w kolejnych kopiach zapasowych.',
    fr_FR:
      'Conserve les derniers réglages du bureau et de l’éditeur lors des sauvegardes successives.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
