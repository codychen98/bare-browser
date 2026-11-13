#!/usr/bin/env bash
# Download baksmali/smali + deps into $1 (default: .fork-tools)
set -euo pipefail
OUT="${1:-.fork-tools}"
mkdir -p "$OUT"
cd "$OUT"

fetch() {
  local url="$1" dest="$2"
  if [[ -f "$dest" ]]; then
    return 0
  fi
  curl -fsSL -o "$dest" "$url"
}

fetch "https://repo1.maven.org/maven2/org/smali/baksmali/2.5.2/baksmali-2.5.2.jar" baksmali.jar
fetch "https://repo1.maven.org/maven2/org/smali/smali/2.5.2/smali-2.5.2.jar" smali.jar
fetch "https://repo1.maven.org/maven2/org/smali/dexlib2/2.5.2/dexlib2-2.5.2.jar" dexlib2.jar
fetch "https://repo1.maven.org/maven2/org/smali/util/2.5.2/util-2.5.2.jar" util.jar
fetch "https://repo1.maven.org/maven2/com/beust/jcommander/1.82/jcommander-1.82.jar" jcommander.jar
fetch "https://repo1.maven.org/maven2/com/google/guava/guava/31.1-jre/guava-31.1-jre.jar" guava.jar
fetch "https://repo1.maven.org/maven2/com/google/guava/failureaccess/1.0.1/failureaccess-1.0.1.jar" failureaccess.jar
fetch "https://repo1.maven.org/maven2/org/antlr/antlr-runtime/3.5.2/antlr-runtime-3.5.2.jar" antlr-runtime.jar
fetch "https://repo1.maven.org/maven2/org/antlr/stringtemplate/3.2.1/stringtemplate-3.2.1.jar" stringtemplate.jar
fetch "https://repo1.maven.org/maven2/antlr/antlr/2.7.7/antlr-2.7.7.jar" antlr.jar

ROOT="$(pwd)"
BAKSMALI_CP="$ROOT/baksmali.jar:$ROOT/dexlib2.jar:$ROOT/util.jar:$ROOT/guava.jar:$ROOT/jcommander.jar:$ROOT/failureaccess.jar"
SMALI_CP="$ROOT/smali.jar:$ROOT/dexlib2.jar:$ROOT/util.jar:$ROOT/guava.jar:$ROOT/jcommander.jar:$ROOT/failureaccess.jar:$ROOT/antlr-runtime.jar:$ROOT/stringtemplate.jar:$ROOT/antlr.jar"
printf '%s\n' "$BAKSMALI_CP" > baksmali.cp
printf '%s\n' "$SMALI_CP" > smali.cp
echo "tools ready in $OUT"
