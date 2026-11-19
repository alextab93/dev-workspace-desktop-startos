import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const v0_1_0_2 = VersionInfo.of({
  version: '0.1.0:2',
  releaseNotes: {
    en_US:
      'Keep an installed editor accessible when an update is pending or fails. Preserve first-install requirements. Fix macOS Command shortcuts stealing editor focus and dropping subsequent typing.',
    es_ES:
      'Mantiene accesible el editor instalado si una actualización está pendiente o falla. Conserva los requisitos de la primera instalación. Corrige los atajos Command de macOS que desviaban el foco y perdían caracteres posteriores.',
    de_DE:
      'Hält den installierten Editor bei ausstehenden oder fehlgeschlagenen Updates zugänglich und behält die Anforderungen der Erstinstallation bei. Behebt Fokusverlust und fehlende Zeichen nach macOS-Command-Tastenkürzeln.',
    pl_PL:
      'Zachowuje dostęp do zainstalowanego edytora, gdy aktualizacja oczekuje lub się nie powiedzie, oraz wymagania pierwszej instalacji. Naprawia skróty Command w macOS, które przenosiły fokus i gubiły później wpisywane znaki.',
    fr_FR:
      'Garde l’éditeur installé accessible lorsqu’une mise à jour est en attente ou échoue et conserve les exigences de première installation. Corrige les raccourcis Command de macOS qui déplaçaient le focus et perdaient les caractères suivants.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
