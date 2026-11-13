# Fork overlays (codychen98/bare-browser)

Custom changes kept out of upstream BareBrowser `patches/`.

## Snackbar toggles

Patched APKs add a second launcher icon: **Bare snackbar settings**.

| Setting | Default | Effect when enabled |
| --- | --- | --- |
| Hide fullscreen exit notice | off (stock) | Suppresses the “To exit full screen…” bar |
| Hide tab-close Undo bar | off (stock) | Suppresses “Closed … / Undo” (still commits the close) |

Prefs live in `SharedPreferences` file `bare_fork_snackbars`.

## CI

On each upstream Bare release (or manual dispatch), Actions:

1. Downloads the official arm64 APK  
2. Patches `SnackbarManager.showSnackbar` to honor the toggles  
3. Injects the settings activity  
4. Resigns with this fork’s keystore and publishes `patched-<tag>`

Package id stays `org.barebrowser`. Uninstall official Bare once before the first fork install; later fork builds update in place and keep data.

## Local private files

Use `.bare-fork-local/` at the repo root for notes/secrets you never want committed.
It is listed in `.gitignore` by this fork. After upstream syncs, confirm that ignore
line is still present.