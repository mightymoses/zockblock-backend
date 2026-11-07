# Tier-Avatar beim Anlegen verpflichtend + Farbe als ARGB reparieren

## Ziel
- Beim Anlegen eines Profils müssen Tier-Avatar (`animalAssetName`) und Farbe (`avatarColor`)
  mitgeschickt werden – sie sind der Rückfall, wenn kein Foto gesetzt ist.
- Bug beheben: Die App schickt `avatarColor` als ARGB-Wert (z. B. `0xFF52A788` = `4283606920`),
  die Spalte war aber `INTEGER` (max. `2147483647`) → jede Farbe mit vollem Alpha ergab eine 500.

## Entscheidungen aus der Planung
- Grund für die bisherige Optionalität war nicht dokumentiert (vermutlich von den nullable
  DB-Spalten übernommen). DB-Spalten bleiben nullable (Bestandskonten), nur die API wird strenger.
- `UserCreate`: `animalAssetName` Pflicht (1–100 Zeichen), `avatarColor` Pflicht (`0 ≤ x ≤ 0xFFFFFFFF`).
- `UserUpdate`: beide optional, explizites `null` → 422 (sonst ließe sich der Rückfall-Avatar löschen).
- Farbe: Spalte auf `BIGINT` statt die App auf RGB ohne Alpha umzustellen (keine App-Änderung nötig).
  Hex vs. dezimal ist nur Schreibweise – die Grenze steht als `0xFFFFFFFF` im Code, JSON liefert die
  Zahl dezimal.
- Downgrade der Migration setzt Farben > `2147483647` auf `NULL`, statt am Typwechsel zu scheitern.

## Dateien
- [x] `app/users/schemas.py`: `MAX_ARGB_COLOR`, Pflichtfelder in `UserCreate`, Constraints +
  Null-Ablehnung in `UserUpdate`
- [x] `app/users/models.py`: `avatar_color` als `BigInteger`
- [x] `app/users/application/command/user_command_service.py`: `animal_asset_name`/`avatar_color`
  in `create_user` ohne Default
- [x] Migration `widen avatar_color to bigint` (upgrade → downgrade → upgrade gegen temporären
  Postgres-Container getestet, inkl. ARGB-Wert)
- [x] Tests: echter ARGB-Wert wird gespeichert/zurückgegeben; Farbe < 0 oder > `0xFFFFFFFF` → 422;
  leerer Tiername → 422; jedes Pflichtfeld fehlt → 422; `null` im PATCH → 422
- [x] `docs/db/schema.dbml`

## Offen (App)
- [ ] Doc-Kommentar an `User` in der App ("Außer `username` ist alles optional") anpassen
