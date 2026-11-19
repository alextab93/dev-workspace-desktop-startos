import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const v0_1_0_6 = VersionInfo.of({
  version: '0.1.0:6',
  releaseNotes: {
    en_US:
      'Documents verified Firefox keyboard shortcuts and saving after reconnect on macOS.',
    es_ES:
      'Documenta los atajos de teclado de Firefox y el guardado tras la reconexión en macOS.',
    de_DE:
      'Dokumentiert die geprüften Firefox-Tastenkürzel und das Speichern nach erneuter Verbindung unter macOS.',
    pl_PL:
      'Dokumentuje sprawdzone skróty klawiaturowe w Firefoksie i zapisywanie po ponownym połączeniu w macOS.',
    fr_FR:
      'Documente les raccourcis clavier vérifiés dans Firefox et l’enregistrement après reconnexion sous macOS.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
