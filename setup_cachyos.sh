#!/usr/bin/env bash
# language: Bash, file: setup_cachyos.sh
# WiFi Killer v4.0 — NETACT × BOWOgaming
# Build APK — CachyOS / Arch Linux / EndeavourOS / Manjaro
set -euo pipefail

RED='\033[0;31m'; TEAL='\033[0;36m'; GOLD='\033[1;33m'; RESET='\033[0m'
info()  { echo -e "${TEAL}[·] $*${RESET}"; }
ok()    { echo -e "${TEAL}[+] $*${RESET}"; }
warn()  { echo -e "${GOLD}[!] $*${RESET}"; }
die()   { echo -e "${RED}[✗] $*${RESET}"; exit 1; }

echo "============================================================"
echo "  WiFi Killer APK Builder v5.0 — NETACT × BOWOgaming"
echo "  Target: Android 6+ (API 23) → Android 13+ (API 33)"
echo "  Arch  : arm64-v8a + armeabi-v7a"
echo "============================================================"
echo

# ── [1] yay ────────────────────────────────────────────────────────────────────
info "[1/7] Pastikan yay tersedia..."
if ! command -v yay &>/dev/null; then
    warn "yay tidak ditemukan — install dari AUR..."
    sudo pacman -S --needed git base-devel --noconfirm
    git clone https://aur.archlinux.org/yay.git /tmp/yay-build-tmp
    cd /tmp/yay-build-tmp && makepkg -si --noconfirm
    cd -
fi
ok "yay $(yay --version | head -1) siap."

# ── [2] deps sistem ────────────────────────────────────────────────────────────
info "[2/7] Install dependensi sistem via pacman..."
sudo pacman -S --needed --noconfirm \
    python python-pip \
    jdk17-openjdk \
    git zip unzip wget \
    cmake ninja \
    libffi openssl \
    autoconf automake libtool \
    pkg-config \
    zlib \
    ccache \
    mdk4 \
    aircrack-ng \
    hcxdumptool

info "Install Android SDK via yay (mungkin lama pertama kali)..."
yay -S --needed --noconfirm \
    android-sdk \
    android-sdk-build-tools \
    android-sdk-platform-tools \
    android-platform || warn "AUR package gagal — buildozer bisa unduh SDK sendiri."

ok "Dependensi sistem terpasang."

# ── [3] JAVA_HOME ──────────────────────────────────────────────────────────────
info "[3/7] Konfigurasi JAVA_HOME..."
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
java -version
grep -qxF "export JAVA_HOME=$JAVA_HOME" ~/.bashrc \
    || echo "export JAVA_HOME=$JAVA_HOME" >> ~/.bashrc

# ── [4] Buildozer + Cython (venv) ─────────────────────────────────────────────
info "[4/7] Install Buildozer + Cython (venv di ~/.wifikiller-build)..."
VENV="$HOME/.wifikiller-build"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip wheel
pip install "cython==3.0.2" buildozer
ok "Buildozer $(buildozer --version) siap."

# ── [5] pre-accept SDK license ────────────────────────────────────────────────
info "[5/7] Pre-accept Android SDK licenses..."
SDK_DIR="$HOME/.buildozer/android/platform/android-sdk"
mkdir -p "$SDK_DIR/licenses"
echo -e "8933bad161af4178b1185d1a37fbf41ea5269c55\nd56f5187479451eabf01fb78af6dfcb131a6481e\n24333f8a63b6825ea9c5514f83c2829b004d1fee" \
    > "$SDK_DIR/licenses/android-sdk-license"
echo -e "84831b9409646a918e30573bab4c9c91346d8abd" \
    > "$SDK_DIR/licenses/android-sdk-preview-license"
ok "SDK licenses di-pre-accept."

# ── [6] siapkan project & build ───────────────────────────────────────────────
info "[6/7] Siapkan folder project & build APK..."
BUILD_DIR="$HOME/wifikiller-apk"
mkdir -p "$BUILD_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/main.py"        "$BUILD_DIR/"
cp "$SCRIPT_DIR/buildozer.spec" "$BUILD_DIR/"
ok "File disalin ke $BUILD_DIR"

cd "$BUILD_DIR"
[[ "${CLEAN:-0}" == "1" ]] && buildozer android clean
buildozer -v android debug 2>&1 | tee build.log

# ── [7] laporan ───────────────────────────────────────────────────────────────
APK=$(find "$BUILD_DIR/bin" -name "*.apk" 2>/dev/null | head -1)
echo
echo "============================================================"
if [[ -n "$APK" ]]; then
    ok "[7/7] BUILD SUKSES!"
    echo -e "  APK  : ${TEAL}$APK${RESET}"
    echo -e "  Size : $(du -sh "$APK" | cut -f1)"
    echo
    echo "  Install: adb install \"$APK\""
    echo
    echo "  CATATAN:"
    echo "  ├─ APK butuh ROOT di device Android"
    echo "  ├─ Install tools di device (Termux / NetHunter):"
    echo "  │     apt install aircrack-ng mdk4 hcxdumptool"
    echo "  └─ Android 6-7: grant izin LOKASI manual"
else
    die "[7/7] APK tidak ditemukan. Cek build.log."
fi
echo
echo "  dibuat oleh NETACT dan BOWOgaming"
echo "============================================================"
deactivate 2>/dev/null || true
