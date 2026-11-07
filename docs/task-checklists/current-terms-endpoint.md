# Endpunkt für die aktuelle Fassung der Nutzungsbedingungen

## Ziel
Die App muss beim Zustimmen genau die aktuelle Version mitschicken (Create/Update akzeptieren nur
`current_terms_version`), hatte aber keinen Weg, sie zu erfahren – neue Nutzer haben noch nicht
einmal ein Profil. Eine Konstante in der App scheidet aus (ältere App-Versionen bekämen nach einem
Bump nur noch 400er).

## Entscheidungen aus der Planung
- `GET /api/terms/current` → `{ "version": "2026-11-01", "url": "https://legal.zockblock.app/terms/2026-11-01" }`
  (camelCase-Schema wie überall). Die App zeigt den Link und schickt genau diese `version` zurück.
- **Öffentlich, ohne Token:** Die Bedingungen sind öffentlich, und die App braucht sie im Onboarding,
  bevor es ein Profil (oder evtl. einen Login) gibt. Ein Token würde nichts schützen.
- **Eigenes Feature `app/terms/`** statt unter `users/`: Die aktuelle Fassung gehört keinem Nutzer,
  die Route liegt unter `/terms`. Keine Tabelle, kein Repository – die Werte kommen aus der Config
  (`CurrentTerms` als einfache Dataclass in `models.py`).
- `terms_acceptance` bleibt in `users/` (pro Nutzer, gleiche Transaktion wie der User).
- **Eine Quelle:** Die Versionsprüfung in `users` ruft `terms_query_service.get_current_terms()`
  statt die Settings direkt zu lesen (Zugriff auf ein fremdes Feature über dessen Service).
  Abgesichert per import-linter-Contract: `app.terms` darf `app.users` nicht importieren.
- **Nicht konfiguriert** (Version oder URL leer): `TermsNotConfiguredException` → 500 + Error-Log,
  sowohl für `GET /terms/current` als auch für Create/Update mit Zustimmung – lieber ein klarer
  Serverfehler als ein leerer String, den die App als "akzeptierte Version" zurückschickt.
- Texte liegen auf GitHub Pages unter `legal.zockblock.app` (Repo `zockblock-legal`), eine Datei
  pro Version.

## Dateien
- [x] `app/config.py`: `current_terms_url: str = ""`
- [x] `.env.example`, `render.yaml`: `CURRENT_TERMS_URL`
- [x] `app/terms/models.py`: `CurrentTerms` (Dataclass, keine Tabelle)
- [x] `app/terms/exceptions.py`: `TermsNotConfiguredException`
- [x] `app/terms/schemas.py`: `TermsResponse` (`version`, `url`)
- [x] `app/terms/application/query/terms_query_service.py`: `get_current_terms()`
- [x] `app/terms/router.py`: `GET /terms/current` ohne `AuthDep`
- [x] `app/main.py`: Router einhängen, Handler → 500
- [x] `app/users/application/command/user_command_service.py`: `_validate_terms_version` nutzt
  `terms_query_service`
- [x] `pyproject.toml`: erster import-linter-Contract (`app.terms` → `app.users` verboten)
- [x] `tests/conftest.py`: `CURRENT_TERMS_URL` setzen + Settings-Cache leeren (sonst sehen Tests ohne
  DB-Fixture die Werte aus der lokalen `.env`)
- [x] Tests: Endpunkt ohne Token → 200 mit Version + URL; Version oder URL leer → 500; Create bei
  fehlender Konfiguration → 500
- [x] `docs/task-checklists/user-consents.md`: Aussage "App muss die Version nicht kennen" korrigiert

## Offen (manuell)
- [ ] In Render prüfen, dass `CURRENT_TERMS_URL` gesetzt ist (ggf. Blueprint-Sync)
- [ ] GitHub Pages: Zertifikat fertig, "Enforce HTTPS" an, `terms/2026-11-01.md` erreichbar
