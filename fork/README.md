# Fork overlays (codychen98/bare-browser)

Custom changes that must not collide with upstream BareBrowser patches.

## Snackbar policy

`snackbar-policy.json` controls how long these native bars stay visible:

- Tab-close Undo (`UMA_TAB_CLOSE_UNDO` / `ALL` / `MULTIPLE`)
- Fullscreen exit notice (`UMA_EXCLUSIVE_ACCESS_BUBBLE`)

`seconds: 0` suppresses the bar (commits pending undo via `onDismissNoAction`).
`seconds: 1` or `2` shows it briefly and bypasses Chromium's accessibility duration floor.

## CI

GitHub Actions downloads each Bare release APK, patches `SnackbarManager.showSnackbar` /
`getDuration` in the DEX (R8 names are discovered each build), resigns with the fork
keystore, and publishes a release asset.

Package id stays `org.barebrowser`. Signature is the fork's, so install requires
uninstalling official Bare once; later fork builds update in place and keep data.
