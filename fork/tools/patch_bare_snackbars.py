#!/usr/bin/env python3
"""Patch a Bare Android APK so snackbar notices can be toggled off at runtime.

Default behavior matches official Bare (notices still show). Users open the
"Bare snackbar settings" launcher entry and enable:
  - hide_fullscreen_exit
  - hide_tab_close_undo
stored in SharedPreferences file bare_fork_snackbars.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


PREF_FILE = "bare_fork_snackbars"
KEY_FULLSCREEN = "hide_fullscreen_exit"
KEY_UNDO = "hide_tab_close_undo"


def run(cmd: list[str], **kwargs) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def find_dex_with_marker(apk: Path, marker: bytes) -> str:
    with zipfile.ZipFile(apk) as zf:
        dexes = sorted(n for n in zf.namelist() if re.fullmatch(r"classes\d*\.dex", n))
        for name in dexes:
            if marker in zf.read(name):
                return name
    raise SystemExit(f"marker {marker!r} not found in any classes*.dex")


def next_dex_name(apk_dir: Path) -> str:
    existing = []
    for p in apk_dir.glob("classes*.dex"):
        m = re.fullmatch(r"classes(\d*)\.dex", p.name)
        if not m:
            continue
        existing.append(1 if m.group(1) == "" else int(m.group(1)))
    n = max(existing) + 1 if existing else 2
    return "classes.dex" if n == 1 else f"classes{n}.dex"


def discover_manager(
    smali_root: Path,
) -> tuple[Path, str, str, str, str, str, str, str, str]:
    manager_file = None
    for path in smali_root.rglob("*.smali"):
        if '"Snackbar.Shown"' in path.read_text(encoding="utf-8", errors="replace"):
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

    activity_m = re.search(
        r"\.field public(?: final)? (\w+):Landroidx/fragment/app/FragmentActivity;",
        text,
    )
    if not activity_m:
        activity_m = re.search(
            r"\.field public(?: final)? (\w+):Landroid/app/Activity;",
            text,
        )
    if not activity_m:
        raise SystemExit("could not discover SnackbarManager activity field")
    activity_field = activity_m.group(1)
    activity_type = (
        "androidx/fragment/app/FragmentActivity"
        if "FragmentActivity" in activity_m.group(0)
        else "android/app/Activity"
    )

    snackbar_file = smali_root / f"{snackbar_type}.smali"
    if not snackbar_file.is_file():
        snackbar_file = next(smali_root.rglob(f"{snackbar_type.split('/')[-1]}.smali"))
    s_text = snackbar_file.read_text(encoding="utf-8", errors="replace")

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
        f"id={id_field} activity={activity_field} controller={controller_field} "
        f"action={action_field}",
        flush=True,
    )
    return (
        manager_file,
        manager_type,
        snackbar_type,
        id_field,
        activity_field,
        activity_type,
        controller_field,
        controller_type,
        action_field,
    )


def find_show_method(text: str) -> str:
    show_m = re.search(
        r"(\.method public final l\(L[^;]+;\)V\n[\s\S]*?\n\.end method)",
        text,
    )
    if not show_m:
        show_m = re.search(
            r"(\.method[^\n]*\n(?:.*\n)*?[^\n]*Snackbar\.Shown[\s\S]*?\n\.end method)",
            text,
        )
    if not show_m:
        raise SystemExit("could not find showSnackbar method")
    return show_m.group(1)


def build_show_prefix(
    manager_type: str,
    snackbar_type: str,
    id_field: str,
    activity_field: str,
    activity_type: str,
    controller_field: str,
    controller_type: str,
    action_field: str,
) -> str:
    # Defaults are false => stock Bare behavior unless the user enables a toggle.
    return f"""
    # [bare-fork] optional snackbar suppression via SharedPreferences
    iget v0, p1, L{snackbar_type};->{id_field}:I

    const/16 v1, 0xb
    if-eq v0, v1, :bare_not_tab_11
    const-string v2, "{KEY_UNDO}"
    goto :bare_check_pref

    :bare_not_tab_11
    const/16 v1, 0xc
    if-eq v0, v1, :bare_not_tab_12
    const-string v2, "{KEY_UNDO}"
    goto :bare_check_pref

    :bare_not_tab_12
    const/16 v1, 0x1e
    if-eq v0, v1, :bare_not_tab_30
    const-string v2, "{KEY_UNDO}"
    goto :bare_check_pref

    :bare_not_tab_30
    const/16 v1, 0x57
    if-eq v0, v1, :bare_after_policy
    const-string v2, "{KEY_FULLSCREEN}"
    goto :bare_check_pref

    :bare_check_pref
    iget-object v0, p0, L{manager_type};->{activity_field}:L{activity_type};
    const-string v1, "{PREF_FILE}"
    const/4 v3, 0x0
    invoke-virtual {{v0, v1, v3}}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v0
    invoke-interface {{v0, v2, v3}}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
    move-result v0
    if-eqz v0, :bare_after_policy

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
    # Inject uses v0-v3 before the original body reloads them.
    regs_m = re.search(r"\.registers (\d+)", method)
    if regs_m and int(regs_m.group(1)) < 6:
        method = re.sub(r"\.registers \d+", ".registers 6", method, count=1)

    m = re.search(
        r"(iget-boolean [^\n]+\n\n(?:[ \t]*\.line[^\n]*\n\n)*[ \t]*if-eqz [^\n]+\n)",
        method,
    )
    if not m:
        m = re.search(r"(if-eqz [^\n]+\n)", method)
        if not m:
            raise SystemExit("could not find early-return guard in showSnackbar")
        insert_at = m.end()
    else:
        insert_at = m.end()
    return method[:insert_at] + prefix + method[insert_at:]


def patch_manager(
    manager_file: Path,
    manager_type: str,
    snackbar_type: str,
    id_field: str,
    activity_field: str,
    activity_type: str,
    controller_field: str,
    controller_type: str,
    action_field: str,
) -> None:
    text = manager_file.read_text(encoding="utf-8")
    show = find_show_method(text)
    prefix = build_show_prefix(
        manager_type,
        snackbar_type,
        id_field,
        activity_field,
        activity_type,
        controller_field,
        controller_type,
        action_field,
    )
    new_show = patch_show_method(show, prefix)
    if show not in text:
        raise SystemExit("internal: show method mismatch")
    manager_file.write_text(text.replace(show, new_show, 1), encoding="utf-8")
    print(f"patched {manager_file}", flush=True)


def inject_manifest(manifest: Path) -> None:
    text = manifest.read_text(encoding="utf-8")
    # aapt2 frameworks shipped with apktool lag new platform attrs; drop them so
    # rebuild succeeds. Runtime behavior we care about does not depend on these.
    text = re.sub(r'\s+\w+:zygotePreloadNativeLib="[^"]*"', "", text)
    text = re.sub(r'\s+\w+:nativeService="[^"]*"', "", text)

    if "org.barebrowser.fork.SnackbarSettingsActivity" not in text:
        prefix = "android"
        m = re.search(
            r'xmlns:(\w+)="http://schemas.android.com/apk/res/android"', text
        )
        if m:
            prefix = m.group(1)
        a = prefix
        block = f"""
        <activity {a}:name="org.barebrowser.fork.SnackbarSettingsActivity" {a}:exported="true" {a}:label="Bare snackbar settings" {a}:theme="@android:style/Theme.DeviceDefault.Light.DarkActionBar">
            <intent-filter>
                <action {a}:name="android.intent.action.MAIN" />
                <category {a}:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
"""
        if "</application>" not in text:
            raise SystemExit("no </application> in manifest")
        text = text.replace("</application>", block + "    </application>", 1)
        print(f"injected settings activity into {manifest}", flush=True)
    else:
        print("manifest already has settings activity", flush=True)

    manifest.write_text(text, encoding="utf-8")


def _is_dex_name(name: str) -> bool:
    return bool(re.fullmatch(r"classes\d*\.dex", name))


def assemble_preserving_resources(
    original_apk: Path, rebuilt_apk: Path, out_apk: Path
) -> None:
    """Build final APK from upstream bytes + apktool overlay.

    Chromium/Bare resources break under apktool decode/rebuild (layouts become
    APKTOOL_DUMMYVAL_*, UrlBar float attrs null → instant launch crash). Keep
    resources.arsc/res/lib/assets from the original APK. Overlay only
    AndroidManifest.xml and classes*.dex from the apktool rebuild. Drop META-INF
    so the CI signer can re-sign.
    """
    with zipfile.ZipFile(rebuilt_apk, "r") as rebuilt:
        overlay_names = [
            n
            for n in rebuilt.namelist()
            if n == "AndroidManifest.xml" or _is_dex_name(n)
        ]
        if "AndroidManifest.xml" not in overlay_names:
            raise SystemExit("rebuilt apk missing AndroidManifest.xml")
        if not any(_is_dex_name(n) for n in overlay_names):
            raise SystemExit("rebuilt apk missing classes*.dex")
        overlay_blobs = {n: rebuilt.read(n) for n in overlay_names}

    overlay_set = set(overlay_names)
    copied = 0
    with zipfile.ZipFile(original_apk, "r") as orig, zipfile.ZipFile(
        out_apk, "w"
    ) as out:
        orig_names = set(orig.namelist())
        for info in orig.infolist():
            name = info.filename
            if name.endswith("/") or name.startswith("META-INF/"):
                continue
            if name in overlay_set:
                continue
            new_info = zipfile.ZipInfo(filename=name, date_time=info.date_time)
            new_info.compress_type = info.compress_type
            new_info.comment = info.comment
            new_info.extra = info.extra
            new_info.create_system = info.create_system
            new_info.external_attr = info.external_attr
            out.writestr(new_info, orig.read(name))
            copied += 1

        for name in sorted(overlay_names):
            if name in orig_names:
                src = orig.getinfo(name)
                new_info = zipfile.ZipInfo(filename=name, date_time=src.date_time)
                new_info.compress_type = src.compress_type
                new_info.external_attr = src.external_attr
            else:
                new_info = zipfile.ZipInfo(filename=name)
                new_info.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(new_info, overlay_blobs[name])

    with zipfile.ZipFile(original_apk, "r") as orig, zipfile.ZipFile(
        out_apk, "r"
    ) as final:
        if orig.read("resources.arsc") != final.read("resources.arsc"):
            raise SystemExit("resources.arsc changed after assemble (abort)")
        if final.read("AndroidManifest.xml") == orig.read("AndroidManifest.xml"):
            raise SystemExit("AndroidManifest.xml was not replaced (abort)")
        final_dex = {n for n in final.namelist() if _is_dex_name(n)}
        if not final_dex >= {n for n in overlay_names if _is_dex_name(n)}:
            raise SystemExit(f"missing overlaid dex in final apk: {final_dex}")

    print(
        f"assembled {out_apk} preserving upstream resources "
        f"(copied={copied}, overlaid={len(overlay_names)})",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baksmali-cp", required=True)
    parser.add_argument("--smali-cp", required=True)
    parser.add_argument("--apktool-jar", type=Path, required=True)
    parser.add_argument(
        "--overlay-smali",
        type=Path,
        required=True,
        help="Directory of fork settings smali (org/barebrowser/fork/...)",
    )
    # retained for workflow compat; ignored (runtime toggles replace bake-in policy)
    parser.add_argument("--policy", type=Path, default=None)
    parser.add_argument("--tab-seconds", type=int, default=None)
    parser.add_argument("--fullscreen-seconds", type=int, default=None)
    args = parser.parse_args()

    work = args.work
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    apktool_dir = work / "apktool"
    run(
        [
            "java",
            "-jar",
            str(args.apktool_jar),
            "d",
            "-f",
            "-s",
            str(args.apk),
            "-o",
            str(apktool_dir),
        ]
    )
    inject_manifest(apktool_dir / "AndroidManifest.xml")

    dex_name = find_dex_with_marker(args.apk, b"Snackbar.Shown")
    print(f"patching {dex_name}", flush=True)
    dex_path = apktool_dir / dex_name
    if not dex_path.is_file():
        # apktool may keep dex under unknown/ in odd layouts; fall back to extract
        with zipfile.ZipFile(args.apk) as zf:
            dex_path.write_bytes(zf.read(dex_name))

    smali_dir = work / "smali-main"
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
        manager_type,
        snackbar_type,
        id_field,
        activity_field,
        activity_type,
        controller_field,
        controller_type,
        action_field,
    ) = discover_manager(smali_dir)

    patch_manager(
        manager_file,
        manager_type,
        snackbar_type,
        id_field,
        activity_field,
        activity_type,
        controller_field,
        controller_type,
        action_field,
    )

    out_dex = work / "patched.dex"
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
    shutil.copy2(out_dex, dex_path)

    # Assemble settings overlay into a new dex
    overlay_out = work / "overlay-smali"
    if overlay_out.exists():
        shutil.rmtree(overlay_out)
    shutil.copytree(args.overlay_smali, overlay_out)
    settings_dex = work / "settings.dex"
    run(
        [
            "java",
            "-cp",
            args.smali_cp,
            "org.jf.smali.Main",
            "a",
            str(overlay_out),
            "-o",
            str(settings_dex),
        ]
    )
    settings_name = next_dex_name(apktool_dir)
    shutil.copy2(settings_dex, apktool_dir / settings_name)
    print(f"added {settings_name} with settings activity", flush=True)

    # apktool rebuild is only used as a source of binary AndroidManifest.xml +
    # patched dex; its re-encoded resources.arsc/res are discarded (see
    # assemble_preserving_resources).
    apktool_unsigned = work / "apktool-unsigned.apk"
    run(
        [
            "java",
            "-jar",
            str(args.apktool_jar),
            "b",
            str(apktool_dir),
            "-o",
            str(apktool_unsigned),
        ]
    )
    if not apktool_unsigned.is_file():
        raise SystemExit("apktool build did not produce apktool-unsigned.apk")
    assemble_preserving_resources(args.apk, apktool_unsigned, args.out)
    print(f"wrote unsigned patched apk {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
