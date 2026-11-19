import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const v0_1_0_5 = VersionInfo.of({
  version: '0.1.0:5',
  releaseNotes: {
    en_US:
      'Updates the guide for opening forwarded ports, unlocking the desktop keyring, and checking browser compatibility.',
    es_ES:
      'Actualiza la guía para abrir puertos reenviados, desbloquear el llavero del escritorio y consultar la compatibilidad de los navegadores.',
    de_DE:
      'Aktualisiert die Anleitung zu weitergeleiteten Ports, zum Entsperren des Desktop-Schlüsselbunds und zur Browserkompatibilität.',
    pl_PL:
      'Aktualizuje instrukcje otwierania przekierowanych portów, odblokowywania pęku kluczy i sprawdzania zgodności przeglądarek.',
    fr_FR:
      'Met à jour le guide des ports redirigés, du déverrouillage du trousseau et de la compatibilité des navigateurs.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
