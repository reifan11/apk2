[app]
# ── identitas ──────────────────────────────────────────────────────────────────
title           = WiFi Killer
package.name    = wifikiller
package.domain  = org.netact
version         = 6.0

# ── sumber ─────────────────────────────────────────────────────────────────────
source.dir          = .
source.include_exts = py,png,kv,atlas

# ── dependensi Python ──────────────────────────────────────────────────────────
# pyjnius  = bridge Python ↔ Android Java (WifiManager, ConnectivityManager)
# android  = p4a Python android module (request_permissions, dll)
# kivy 2.3.0 stabil untuk p4a + API 23-33
requirements = python3,kivy==2.3.0,pyjnius,android

# ── tampilan ───────────────────────────────────────────────────────────────────
orientation  = portrait
fullscreen   = 1

# ── android ────────────────────────────────────────────────────────────────────
# minapi 23 = Android 6.0 Marshmallow
# api 33     = Android 13
android.api              = 33
android.minapi           = 23
android.sdk              = 33

# FIX: format NDK harus full revision string, bukan "25b"
# "25b" menyebabkan buildozer crash saat resolve NDK path
android.ndk              = 25.2.9519653
android.ndk_api          = 23

# arm64-v8a  → Android 8+ 64-bit
# armeabi-v7a → Android 6+ 32-bit (hp lama)
android.archs            = arm64-v8a,armeabi-v7a

# wajib — biar build tidak hang nunggu input manual
android.accept_sdk_license = True

android.allow_backup     = False

# ── permissions ────────────────────────────────────────────────────────────────
# NEARBY_WIFI_DEVICES: Android 13+ (API 33) ganti ACCESS_FINE_LOCATION untuk scan Wi-Fi
# ACCESS_FINE_LOCATION: wajib Android 6-12 untuk scan Wi-Fi
# CHANGE_NETWORK_STATE: untuk disconnect/reconnect
# FIX: ACCESS_BACKGROUND_LOCATION dihapus dari sini — dideclare via
#      extra_manifest_xml dengan maxSdkVersion=28 agar tidak conflict API 29+
android.permissions = INTERNET, \
                      ACCESS_WIFI_STATE, \
                      CHANGE_WIFI_STATE, \
                      ACCESS_NETWORK_STATE, \
                      CHANGE_NETWORK_STATE, \
                      ACCESS_FINE_LOCATION, \
                      ACCESS_COARSE_LOCATION, \
                      CHANGE_WIFI_MULTICAST_STATE

# FIX: NEARBY_WIFI_DEVICES butuh usesPermissionFlags="neverForLocation" untuk
#      compile di API 33. ACCESS_BACKGROUND_LOCATION butuh maxSdkVersion=28.
#      Keduanya tidak bisa di-express via android.permissions biasa.
android.extra_manifest_xml = \
    <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" android:maxSdkVersion="28"/> \
    <uses-permission android:name="android.permission.NEARBY_WIFI_DEVICES" android:usesPermissionFlags="neverForLocation"/>

# ── fitur hardware ─────────────────────────────────────────────────────────────
android.features         = android.hardware.wifi

# ── p4a branch ─────────────────────────────────────────────────────────────────
# FIX: p4a stable release kadang tidak support kivy==2.3.0 di dual-arch build
# develop branch sudah fix bug armv7a+arm64 recipe conflict pada kivy 2.3.x
p4a.branch = develop

# ── gradle / build tools ───────────────────────────────────────────────────────
# FIX: pin build tools agar tidak random ambil versi incompatible
android.add_gradle_maven_repos = https://maven.google.com
android.gradle_dependencies =
# android.build_tools_version = 34.0.0

# ── logcat filter (debug only) ─────────────────────────────────────────────────
android.logcat_filters   = *:S python:D

# ── ikon ───────────────────────────────────────────────────────────────────────
# icon.filename = %(source.dir)s/wifikiller.png
# presplash.filename = %(source.dir)s/presplash.png

[buildozer]
log_level   = 2
warn_on_root = 1
