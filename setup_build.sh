#!/usr/bin/env bash
# language: Bash, file: setup_build.sh
# WiFi Killer v6.0 — NETACT × BOWOgaming
# Build APK — Ubuntu 22.04 / 24.04 / Debian 12 / Kali 2024+
# Jalankan: chmod +x setup_build.sh && ./setup_build.sh
set -euo pipefail

RED='\033[0;31m'; TEAL='\033[0;36m'; GOLD='\033[1;33m'; RESET='\033[0m'
info()  { echo -e "${TEAL}[·] $*${RESET}"; }
ok()    { echo -e "${TEAL}[+] $*${RESET}"; }
warn()  { echo -e "${GOLD}[!] $*${RESET}"; }
die()   { echo -e "${RED}[✗] $*${RESET}"; exit 1; }

echo "============================================================"
echo "  WiFi Killer APK Builder v6.0 — NETACT × BOWOgaming"
echo "  Target: Android 6+ (API 23) → Android 13+ (API 33)"
echo "  Arch  : arm64-v8a + armeabi-v7a"
echo "============================================================"
echo

# ── [0] cek OS ─────────────────────────────────────────────────────────────────
OS_ID=$(. /etc/os-release && echo "$ID")
info "Detected OS: $OS_ID"
case "$OS_ID" in
    ubuntu|debian|kali|linuxmint) ;;
    *) warn "Script ini dioptimalkan untuk Debian/Ubuntu/Kali. Lanjut dengan risiko sendiri.";;
esac

# ── [1] update & install deps sistem ───────────────────────────────────────────
info "[1/7] Install dependensi sistem..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    openjdk-17-jdk-headless \
    git zip unzip wget curl \
    build-essential cmake ninja-build \
    libssl-dev libffi-dev \
    autoconf automake libtool pkg-config \
    zlib1g-dev libncurses5-dev \
    libsqlite3-dev \
    ccache \
    lld \
    aidl

ok "Dependensi sistem terpasang."

# ── [2] set JAVA_HOME ──────────────────────────────────────────────────────────
info "[2/7] Konfigurasi JAVA_HOME..."
export JAVA_HOME=$(readlink -f /usr/bin/javac | sed 's|/bin/javac||')
export PATH="$JAVA_HOME/bin:$PATH"
java -version
grep -qxF "export JAVA_HOME=$JAVA_HOME" ~/.bashrc \
    || echo "export JAVA_HOME=$JAVA_HOME" >> ~/.bashrc

# ── [3] install Buildozer + Cython di virtualenv ───────────────────────────────
info "[3/7] Install Buildozer + Cython (venv di ~/.wifikiller-build)..."
VENV="$HOME/.wifikiller-build"
python3 -m venv "$VENV"
source "$VENV/bin/activate"

# FIX: Cython 3.0.2 stabil untuk p4a / kivy 2.3
# FIX: buildozer dari git agar dapat fix p4a.branch=develop support
pip install --upgrade pip wheel
pip install "cython==3.0.2" buildozer

ok "Buildozer $(buildozer --version) siap."

# ── [4] Android SDK license pre-accept ─────────────────────────────────────────
info "[4/7] Pre-accept Android SDK licenses..."
SDK_DIR="$HOME/.buildozer/android/platform/android-sdk"
mkdir -p "$SDK_DIR/licenses"
# SHA dari license teks Google (stable sejak 2015)
echo -e "8933bad161af4178b1185d1a37fbf41ea5269c55\nd56f5187479451eabf01fb78af6dfcb131a6481e\n24333f8a63b6825ea9c5514f83c2829b004d1fee" \
    > "$SDK_DIR/licenses/android-sdk-license"
echo -e "84831b9409646a918e30573bab4c9c91346d8abd" \
    > "$SDK_DIR/licenses/android-sdk-preview-license"
ok "SDK licenses di-pre-accept."

# ── [5] siapkan folder project ────────────────────────────────────────────────
info "[5/7] Siapkan folder project..."
BUILD_DIR="$HOME/wifikiller-apk"
mkdir -p "$BUILD_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/main.py"        "$BUILD_DIR/"
cp "$SCRIPT_DIR/buildozer.spec" "$BUILD_DIR/"
ok "File disalin ke $BUILD_DIR"

# ── [6] build APK ─────────────────────────────────────────────────────────────
info "[6/7] Build APK (proses ini bisa 30-60 menit pertama kali)..."
cd "$BUILD_DIR"

# Bersihkan cache lama kalau ada error sebelumnya
if [[ "${CLEAN:-0}" == "1" ]]; then
    warn "CLEAN=1 → hapus .buildozer cache..."
    buildozer android clean
fi

# FIX: set ANDROID_SDK_ROOT eksplisit agar buildozer tidak bingung PATH
export ANDROID_SDK_ROOT="$HOME/.buildozer/android/platform/android-sdk"
export ANDROID_NDK_HOME="$HOME/.buildozer/android/platform/android-ndk-r25b"

# Build debug APK — tidak perlu keystore
buildozer -v android debug 2>&1 | tee build.log

# ── [7] laporan ───────────────────────────────────────────────────────────────
APK=$(find "$BUILD_DIR/bin" -name "*.apk" 2>/dev/null | head -1)
echo
echo "============================================================"
if [[ -n "$APK" ]]; then
    ok "[7/7] BUILD SUKSES!"
    echo -e "  APK    : ${TEAL}$APK${RESET}"
    echo -e "  Size   : $(du -sh "$APK" | cut -f1)"
    echo
    echo "  Install via ADB:"
    echo -e "    ${GOLD}adb install \"$APK\"${RESET}"
    echo
    echo "  CATATAN:"
    echo "  ├─ Android 6-7 (API 23-25): izin lokasi harus di-grant manual di Settings"
    echo "  ├─ Android 13+ (API 33): izin NEARBY_WIFI_DEVICES muncul otomatis"
    echo "  ├─ Fitur MDK4/deauth/beacon: butuh root + monitor mode di device"
    echo "  └─ DDOS engine (UDP/TCP/HTTP): jalan tanpa root"
else
    die "[7/7] APK tidak ditemukan. Cek build.log untuk detail error."
    echo "  Tip: jalankan ulang dengan CLEAN=1 ./setup_build.sh"
fi
echo
echo "  dibuat oleh NETACT dan BOWOgaming"
echo "============================================================"

deactivate 2>/dev/null || true
