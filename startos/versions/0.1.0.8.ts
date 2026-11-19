import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const v0_1_0_8 = VersionInfo.of({
  version: '0.1.0:8',
  releaseNotes: {
    en_US: 'Report when the authenticated desktop stream becomes unavailable.',
    es_ES:
      'Indica cuándo deja de estar disponible la transmisión autenticada del escritorio.',
    de_DE:
      'Meldet, wenn der authentifizierte Desktop-Stream nicht erreichbar ist.',
    pl_PL: 'Informuje o niedostępności uwierzytelnionej transmisji pulpitu.',
    fr_FR: 'Signale quand le flux authentifié du bureau devient indisponible.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
