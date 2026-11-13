#!/usr/bin/env python3
"""Patch Bare/Chromium Android APK snackbar durations for tab-close undo and
fullscreen exit notice.

Discovers R8-obfuscated SnackbarManager via the "Snackbar.Shown" histogram
string, then rewrites showSnackbar + getDuration so policy seconds apply even
when accessibility services would otherwise stretch timeouts.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


TAB_CLOSE_IDS = (11, 12, 30)  # UMA_TAB_CLOSE_UNDO / ALL / MULTIPLE
FULLSCREEN_ID = 87  # UMA_EXCLUSIVE_ACCESS_BUBBLE


def run(cmd: list[str], **kwargs) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def load_policy(path: Path, tab_override: int | None, fs_override: int | None) -> tuple[int, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tab = int(data.get("tab_close_undo_seconds", 0))
    fs = int(data.get("fullscreen_exit_seconds", 0))
    if tab_override is not None:
        tab = tab_override
    if fs_override is not None:
        fs = fs_override
    for name, value in (("tab_close_undo_seconds", tab), ("fullscreen_exit_seconds", fs)):
        if value not in (0, 1, 2):
            raise SystemExit(f"{name} must be 0, 1, or 2 (got {value})")
    return tab, fs


def find_dex_with_marker(apk: Path, marker: bytes) -> str:
    with zipfile.ZipFile(apk) as zf:
        dexes = sorted(n for n in zf.namelist() if re.fullmatch(r"classes\d*\.dex", n))
        for name in dexes:
            if marker in zf.read(name):
                return name
    raise SystemExit(f"marker {marker!r} not found in any classes*.dex")


def discover_manager(
    smali_root: Path,
) -> tuple[Path, str, str, str, str, str, str, str]:
    """Return manager path + type names/fields needed to patch show/getDuration."""
    manager_file = None
    for path in smali_root.rglob("*.smali"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if '"Snackbar.Shown"' in text:
            manager_file = path
            break
    if manager_file is None:
        raise SystemExit('could not find SnackbarManager (no "Snackbar.Shown")')

    text = manager_file.read_text(encoding="utf-8", errors="replace")
    class_m = re.search(r"^\.class .* L([^;]+);", text, re.M)
    if not class_m:
        raise SystemExit(f"no .class in {manager_file}")
    manager_type = class_m.group(1)

    shown_idx = text.find('"Snackbar.Shown"')
    window = text[max(0, shown_idx - 800) : shown_idx]
    id_m = re.search(r"iget[^\n]* p1, L([^;]+);->(\w+):I", window)
    if not id_m:
        raise SystemExit("could not discover snackbar identifier field")
    snackbar_type, id_field = id_m.group(1), id_m.group(2)

    snackbar_file = smali_root / f"{snackbar_type}.smali"
    if not snackbar_file.is_file():
        candidates = list(smali_root.rglob(f"{snackbar_type.split('/')[-1]}.smali"))
        if not candidates:
            raise SystemExit(f"missing snackbar smali for {snackbar_type}")
        snackbar_file = candidates[0]
    s_text = snackbar_file.read_text(encoding="utf-8", errors="replace")

    # Duration field from getDuration: first iget of int from p0 after method start near 0xbb8
    dur_window_m = re.search(
        r"\.method public static \w+\(L[^;]+;\)I\n[\s\S]*?0xbb8[\s\S]*?\n\.end method",
        text,
    )
    if not dur_window_m:
        raise SystemExit("could not locate getDuration for duration field discovery")
    dur_iget = re.search(
        rf"iget[^\n]* p0, L{re.escape(snackbar_type)};->(\w+):I",
        dur_window_m.group(0),
    )
    if not dur_iget:
        raise SystemExit("could not discover snackbar duration field")
    duration_field = dur_iget.group(1)

    # Dismiss path: invoke-interface ..., LCtrl;->b(Object) with snackbar controller + actionData
    dismiss_m = re.search(
        rf"iget-object (\w+), (\w+), L{re.escape(snackbar_type)};->(\w+):L([^;]+);\n"
        rf"[\s\S]{{0,200}}?"
        rf"iget-object (\w+), \2, L{re.escape(snackbar_type)};->(\w+):Ljava/lang/Object;\n"
        rf"[\s\S]{{0,80}}?"
        rf"invoke-interface \{{\1, \5}}, L\4;->b\(Ljava/lang/Object;\)V",
        text,
    )
    if dismiss_m:
        controller_field = dismiss_m.group(3)
        controller_type = dismiss_m.group(4)
        action_field = dismiss_m.group(6)
    else:
        # Fallback: first custom-typed field + java.lang.Object field on snackbar
        controller_field = None
        controller_type = None
        for m in re.finditer(r"\.field public(?: final)? (\w+):L([^;]+);", s_text):
            field, typ = m.group(1), m.group(2)
            if typ.startswith(("android/", "java/")):
                continue
            controller_field, controller_type = field, typ
            break
        action_m = re.search(
            r"\.field public(?: final)? (\w+):Ljava/lang/Object;",
            s_text,
        )
        if controller_field is None or action_m is None:
            raise SystemExit("could not discover snackbar controller/action fields")
        action_field = action_m.group(1)

    print(
        f"discovered manager=L{manager_type}; snackbar=L{snackbar_type}; "
        f"id={id_field} duration={duration_field} controller={controller_field}:"
        f"L{controller_type}; action={action_field}",
        flush=True,
    )
    return (
        manager_file,
        manager_type,
        snackbar_type,
        id_field,
        duration_field,
        controller_field,
        controller_type,
        action_field,
    )


def find_show_and_duration_methods(text: str) -> tuple[str, str]:
    show_m = re.search(
        r"(\.method public final l\(L[^;]+;\)V\n[\s\S]*?\n\.end method)",
        text,
    )
    if not show_m:
        # some builds may not use name 'l' — find method containing Snackbar.Shown
        show_m = re.search(
            r"(\.method[^\n]*\n(?:.*\n)*?[^\n]*Snackbar\.Shown[\s\S]*?\n\.end method)",
            text,
        )
    if not show_m:
        raise SystemExit("could not find showSnackbar method")

    dur_m = re.search(
        r"(\.method public static \w+\(L[^;]+;\)I\n[\s\S]*?0xbb8[\s\S]*?AccessibilityState[\s\S]*?\n\.end method)",
        text,
    )
    if not dur_m:
        raise SystemExit("could not find getDuration method (0xbb8 + AccessibilityState)")
    return show_m.group(1), dur_m.group(1)


def build_show_prefix(
    snackbar_type: str,
    id_field: str,
    duration_field: str,
    controller_field: str,
    controller_type: str,
    action_field: str,
    tab_ms: int,
    fs_ms: int,
) -> str:
    """Smali inserted immediately after the activity-foreground early-return guard."""
    return f"""
    # [bare-fork] snackbar policy tab_ms={tab_ms} fs_ms={fs_ms}
    iget v0, p1, L{snackbar_type};->{id_field}:I

    const/16 v1, 0xb
    if-eq v0, v1, :bare_not_tab_close_undo

    goto :bare_handle_tab_close

    :bare_not_tab_close_undo
    const/16 v1, 0xc
    if-eq v0, v1, :bare_not_tab_close_all

    goto :bare_handle_tab_close

    :bare_not_tab_close_all
    const/16 v1, 0x1e
    if-eq v0, v1, :bare_not_tab_close_multi

    goto :bare_handle_tab_close

    :bare_not_tab_close_multi
    const/16 v1, 0x57
    if-eq v0, v1, :bare_after_policy

    goto :bare_handle_fullscreen

    :bare_handle_tab_close
    const/16 v1, {tab_ms}
    if-lez v1, :bare_suppress

    iput v1, p1, L{snackbar_type};->{duration_field}:I
    goto :bare_after_policy

    :bare_handle_fullscreen
    const/16 v1, {fs_ms}
    if-lez v1, :bare_suppress

    iput v1, p1, L{snackbar_type};->{duration_field}:I
    goto :bare_after_policy

    :bare_suppress
    iget-object v0, p1, L{snackbar_type};->{controller_field}:L{controller_type};
    if-eqz v0, :bare_return

    iget-object v1, p1, L{snackbar_type};->{action_field}:Ljava/lang/Object;
    invoke-interface {{v0, v1}}, L{controller_type};->b(Ljava/lang/Object;)V

    :bare_return
    return-void

    :bare_after_policy
"""


def patch_show_method(method: str, prefix: str) -> str:
    if "[bare-fork]" in method:
        raise SystemExit("showSnackbar already patched")
    # After foreground guard: iget-boolean ..., if-eqz ..., then our code
    m = re.search(
        r"(iget-boolean [^\n]+\n\n(?:[ \t]*\.line[^\n]*\n\n)*[ \t]*if-eqz [^\n]+\n)",
        method,
    )
    if not m:
        # looser: first if-eqz after method start
        m = re.search(r"(if-eqz [^\n]+\n)", method)
        if not m:
            raise SystemExit("could not find early-return guard in showSnackbar")
        insert_at = m.end()
    else:
        insert_at = m.end()
    return method[:insert_at] + prefix + method[insert_at:]


def patch_duration_method(
    method: str,
    snackbar_type: str,
    id_field: str,
    duration_field: str,
) -> str:
    if "[bare-fork]" in method:
        raise SystemExit("getDuration already patched")
    # Replace body with policy-aware version that still falls back to original
    # by jumping into the original first instruction after our check.
    m = re.match(r"(\.method[^\n]+\n[ \t]*\.registers[^\n]+\n)", method)
    if not m:
        raise SystemExit("bad getDuration header")
    header = m.group(1)
    rest = method[m.end() :]
    inject = f"""
    # [bare-fork] honor baked duration for tab-close / fullscreen ids (bypass a11y floor)
    iget v0, p0, L{snackbar_type};->{id_field}:I

    const/16 v1, 0xb
    if-eq v0, v1, :bare_dur_not_11
    goto :bare_dur_forced

    :bare_dur_not_11
    const/16 v1, 0xc
    if-eq v0, v1, :bare_dur_not_12
    goto :bare_dur_forced

    :bare_dur_not_12
    const/16 v1, 0x1e
    if-eq v0, v1, :bare_dur_not_30
    goto :bare_dur_forced

    :bare_dur_not_30
    const/16 v1, 0x57
    if-eq v0, v1, :bare_dur_original
    goto :bare_dur_forced

    :bare_dur_forced
    iget v0, p0, L{snackbar_type};->{duration_field}:I
    if-lez v0, :bare_dur_original
    return v0

    :bare_dur_original
"""
    # Ensure registers >= 3 (p0 + v0 + v1). Static method with 1 param.
    regs_m = re.search(r"\.registers (\d+)", header)
    if regs_m and int(regs_m.group(1)) < 3:
        header = re.sub(r"\.registers \d+", ".registers 3", header)
    return header + inject + rest


def patch_manager_smali(
    manager_file: Path,
    snackbar_type: str,
    id_field: str,
    duration_field: str,
    controller_field: str,
    controller_type: str,
    action_field: str,
    tab_seconds: int,
    fs_seconds: int,
) -> None:
    text = manager_file.read_text(encoding="utf-8")
    show, duration = find_show_and_duration_methods(text)
    prefix = build_show_prefix(
        snackbar_type=snackbar_type,
        id_field=id_field,
        duration_field=duration_field,
        controller_field=controller_field,
        controller_type=controller_type,
        action_field=action_field,
        tab_ms=tab_seconds * 1000,
        fs_ms=fs_seconds * 1000,
    )
    new_show = patch_show_method(show, prefix)
    new_duration = patch_duration_method(
        duration, snackbar_type, id_field, duration_field
    )
    if show not in text or duration not in text:
        raise SystemExit("internal: method text mismatch")
    text = text.replace(show, new_show, 1).replace(duration, new_duration, 1)
    manager_file.write_text(text, encoding="utf-8")
    print(f"patched {manager_file}", flush=True)


def rebuild_apk(
    src_apk: Path,
    dex_name: str,
    new_dex: Path,
    out_apk: Path,
) -> None:
    if out_apk.exists():
        out_apk.unlink()
    with zipfile.ZipFile(src_apk, "r") as zin, zipfile.ZipFile(
        out_apk,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename.startswith("META-INF/"):
                continue
            if info.filename == dex_name:
                data = new_dex.read_bytes()
            # keep stored for stored entries (native libs often stored)
            if info.compress_type == zipfile.ZIP_STORED:
                zout.writestr(info, data, compress_type=zipfile.ZIP_STORED)
            else:
                zout.writestr(info.filename, data, compress_type=zipfile.ZIP_DEFLATED)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baksmali-cp", required=True, help="classpath for baksmali Main")
    parser.add_argument("--smali-cp", required=True, help="classpath for smali Main")
    parser.add_argument("--tab-seconds", type=int, default=None)
    parser.add_argument("--fullscreen-seconds", type=int, default=None)
    args = parser.parse_args()

    tab_s, fs_s = load_policy(args.policy, args.tab_seconds, args.fullscreen_seconds)
    print(f"policy tab_close={tab_s}s fullscreen={fs_s}s", flush=True)

    work = args.work
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    dex_name = find_dex_with_marker(args.apk, b"Snackbar.Shown")
    print(f"using {dex_name}", flush=True)
    dex_path = work / dex_name
    with zipfile.ZipFile(args.apk) as zf:
        dex_path.write_bytes(zf.read(dex_name))

    smali_dir = work / "smali"
    run(
        [
            "java",
            "-cp",
            args.baksmali_cp,
            "org.jf.baksmali.Main",
            "d",
            str(dex_path),
            "-o",
            str(smali_dir),
        ]
    )

    (
        manager_file,
        _manager_type,
        snackbar_type,
        id_field,
        duration_field,
        controller_field,
        controller_type,
        action_field,
    ) = discover_manager(smali_dir)
    patch_manager_smali(
        manager_file,
        snackbar_type,
        id_field,
        duration_field,
        controller_field,
        controller_type,
        action_field,
        tab_s,
        fs_s,
    )

    out_dex = work / "out.dex"
    run(
        [
            "java",
            "-cp",
            args.smali_cp,
            "org.jf.smali.Main",
            "a",
            str(smali_dir),
            "-o",
            str(out_dex),
        ]
    )

    unsigned = work / "unsigned.apk"
    rebuild_apk(args.apk, dex_name, out_dex, unsigned)
    shutil.copy2(unsigned, args.out)
    print(f"wrote unsigned patched apk {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
