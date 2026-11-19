import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.1.0:9',
  releaseNotes: {
    en_US: 'Check every volume before starting a backup or restore.',
    es_ES:
      'Comprueba todos los volúmenes antes de iniciar una copia de seguridad o una restauración.',
    de_DE:
      'Prüft alle Volumes vor dem Start einer Sicherung oder Wiederherstellung.',
    pl_PL:
      'Sprawdza wszystkie woluminy przed rozpoczęciem tworzenia kopii zapasowej lub przywracania.',
    fr_FR:
      'Vérifie tous les volumes avant de commencer une sauvegarde ou une restauration.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
