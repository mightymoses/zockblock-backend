# Avatar-Uploads über `pending/` (keine verwaisten Bilder in R2)

## Ziel
Hochgeladene Avatar-Bilder, die nie in einem Profil landen (Bild nochmal gewechselt, Onboarding
abgebrochen), sollen automatisch aus R2 verschwinden. Bilder, die tatsächlich im Profil stehen,
bleiben dauerhaft. Ersetzte/entfernte Profilbilder werden sofort gelöscht.

## Entscheidungen aus der Planung
- Upload-URL zeigt auf `pending/avatars/{auth0-sub}/{uuid}.{ext}`. Eine R2-Lifecycle-Regel löscht
  alles unter `pending/` nach 1 Tag (kleinste Einheit bei R2, Löschung erfolgt typischerweise
  innerhalb von 24 h danach).
- Endgültiger Ort: `avatars/{auth0-sub}/{uuid}.{ext}` (= Pending-Key ohne `pending/`-Präfix, so lässt
  sich der eine Key immer aus dem anderen ableiten).
- API-Vertrag bleibt: Die App schickt die erhaltene (Pending-)`avatarUrl` bei Create/Update mit, die
  Response enthält die endgültige URL.
- Gültige Werte für `avatarUrl` bei Create/Update:
  | Wert | Reaktion |
  | --- | --- |
  | eigene Pending-URL (`pending/avatars/{eigener sub}/...`) | übernehmen (kopieren nach `avatars/`) |
  | `null` | Foto entfernen, altes Bild löschen (nur Update) |
  | exakt die aktuell gespeicherte URL | No-op (nur Update) |
  | alles andere (fremder sub, fremde Domain, `avatars/...` ≠ aktuelle) | 400 `InvalidAvatarUrlException` |
  | eigene Pending-URL, Objekt existiert aber nicht in R2 | 400 `InvalidAvatarUrlException` |
- Ablauf beim Übernehmen: **Kopieren** (nicht verschieben) nach `avatars/` direkt vor dem Commit,
  nachdem alle anderen Prüfungen (Username, `avatar_mode`) durch sind.
  - Commit erfolgreich → Pending-Original löschen, ggf. altes Profilbild löschen.
  - Commit (oder irgendetwas danach bis zum Commit) scheitert → Kopie unter `avatars/` löschen,
    Pending-Original bleibt, App kann es erneut versuchen.
  - Löschfehler werden nur geloggt, nicht an den Nutzer weitergegeben (verwaistes Bild ist
    ärgerlich, aber kein Fehler; `pending/` räumt die Lifecycle-Regel ohnehin auf).
- Kein separates `HeadObject` vor dem Kopieren: `CopyObject` schlägt bei fehlender Quelle selbst
  fehl → `storage` übersetzt das in eine eigene `StorageObjectNotFoundError`.
- R2-Token: bestehendes Token (Object Read & Write, auf den Bucket beschränkt) deckt Copy/Delete ab,
  keine neuen Berechtigungen nötig.

## Dateien
- [x] `app/common/storage.py`
  - [x] `PENDING_PREFIX = "pending/"`
  - [x] `StorageObjectNotFoundError`
  - [x] `public_url_for_key(key)` / `key_from_public_url(url) -> str | None`
  - [x] `generate_presigned_upload_url` nutzt `public_url_for_key`
  - [x] `copy_object(source_key, target_key)` (wirft `StorageObjectNotFoundError`)
  - [x] `delete_object(key)`
- [x] `app/users/application/command/user_command_service.py`
  - [x] `request_avatar_upload_url`: Key unter `pending/avatars/{sub}/...`
  - [x] `_validate_avatar_url` ersetzen durch Prüfung "eigene Pending-URL" → liefert Pending-Key
  - [x] `create_user`: Bild nach allen Prüfungen kopieren, Commit, danach Pending löschen bzw. bei
    Fehler Kopie löschen
  - [x] `update_user`: No-op bei unveränderter URL, `null` → altes Bild nach Commit löschen, neue
    Pending-URL → kopieren, nach Commit Pending + altes Bild löschen, bei Fehler Kopie löschen
  - [x] Hilfsfunktion zum "stillen" Löschen (Fehler nur loggen)
  - [x] Nebenbei gefundener Bug: `repository.add()` flusht bereits, ein Unique-Verstoß beim Username
    kam daher schon dort (500) statt im Commit-`try` an. `repository.add()` liegt jetzt mit im
    `try` (`_save_or_raise_if_username_taken`) → korrekt 409, und die Avatar-Kopie wird aufgeräumt
- [x] `tests/conftest.py`: Fake-Storage-Fixture (merkt sich vorhandene Keys, Kopien, Löschungen)
  statt echter R2-Aufrufe
- [x] `tests/users/test_user_router.py`
  - [x] bestehende Avatar-Tests auf Pending-URLs umstellen
  - [x] Create mit eigener Pending-URL → endgültige URL in Response, Pending gelöscht
  - [x] fremde Pending-URL / fremde `avatars/`-URL / nicht existierendes Objekt → 400
  - [x] Update mit unveränderter URL → 200, keine Storage-Aufrufe
  - [x] Update mit neuem Bild → altes Bild + Pending gelöscht
  - [x] Update auf `null` → altes Bild gelöscht
  - [x] Commit scheitert (Username vergeben) → Kopie gelöscht, Pending bleibt
  - [x] Upload-URL zeigt auf `pending/avatars/{sub}/`

## R2-Einrichtung (manuell, Dashboard)
- [x] Lifecycle-Regel für Präfix `pending/` anlegen: Objekte nach 1 Tag löschen
- [ ] Regel kontrollieren (z. B. `npx wrangler r2 bucket lifecycle list <BUCKET>`)
