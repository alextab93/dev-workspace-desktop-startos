import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const v0_1_0_3 = VersionInfo.of({
  version: '0.1.0:3',
  releaseNotes: {
    en_US:
      'Manage the desktop keyring through masked StartOS actions. Create or change its password without deleting saved credentials, unlock after restart, and open VS Code using the same protected session.',
    es_ES:
      'Gestiona el llavero del escritorio con acciones protegidas de StartOS. Crea o cambia su contraseña sin borrar credenciales, desbloquéalo tras reiniciar y abre VS Code en la misma sesión protegida.',
    de_DE:
      'Verwaltet den Desktop-Schlüsselbund über maskierte StartOS-Aktionen. Erstellt oder ändert das Passwort ohne Löschen gespeicherter Zugangsdaten, entsperrt nach Neustarts und öffnet VS Code in derselben geschützten Sitzung.',
    pl_PL:
      'Zarządzaj pękiem kluczy pulpitu przez chronione akcje StartOS. Twórz lub zmieniaj hasło bez usuwania danych logowania, odblokuj po restarcie i otwieraj VS Code w tej samej chronionej sesji.',
    fr_FR:
      'Gérez le trousseau du bureau avec des actions StartOS masquées. Créez ou modifiez son mot de passe sans supprimer les identifiants, déverrouillez après redémarrage et ouvrez VS Code dans la même session protégée.',
  },
  migrations: {
    up: async () => {},
    down: IMPOSSIBLE,
  },
})
