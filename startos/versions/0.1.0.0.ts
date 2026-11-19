import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const v0_1_0_0 = VersionInfo.of({
  version: '0.1.0:0',
  releaseNotes: {
    en_US:
      'Desktop companion candidate with explicit editor installation, protected access and dedicated Dev Workspace SSH pairing.',
    es_ES:
      'Candidato del escritorio con instalación explícita del editor, acceso protegido y conexión SSH dedicada a Dev Workspace.',
    de_DE:
      'Desktop-Kandidat mit ausdrücklicher Editorinstallation, geschütztem Zugriff und eigener SSH-Kopplung mit Dev Workspace.',
    pl_PL:
      'Wersja testowa pulpitu z jawną instalacją edytora, chronionym dostępem i dedykowanym parowaniem SSH z Dev Workspace.',
    fr_FR:
      'Candidat du bureau avec installation explicite de l’éditeur, accès protégé et association SSH dédiée à Dev Workspace.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
