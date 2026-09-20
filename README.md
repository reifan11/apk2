# WiFi Killer v6.0 — NETACT × BOWOgaming
## Non-Root + DDOS Engine Edition

---

### Perubahan v6.0 vs v5.0

| Fitur | v5.0 | v6.0 |
|-------|------|-------|
| Tab DDOS | ✗ | ✓ UDP/TCP/ICMP/HTTP/Slowloris/Combo |
| MDK4 Beacon Flood | ✗ | ✓ (root) — ratusan SSID palsu |
| MDK4 Deauth Storm | ✗ | ✓ (root) — semua klien dikeluarkan |
| Channel Hopper | ✗ | ✓ (root) — lompat kanal 1-13 otomatis |
| Burst Scan | ✗ | ✓ throttle buster 5x trigger |
| Signal Tracker | ✗ | ✓ riwayat sinyal per BSSID |
| Copy GW → DDOS | ✗ | ✓ tombol sekali klik |
| PPS live counter | ✗ | ✓ paket/detik live di stat bar |
| Deauth count slider | ✗ | ✓ kontrol --deauth N |
| MAC address info | ✗ | ✓ tab INFO |
| Log auto-trim | ✗ | ✓ max 200 baris |

---

### Tab DDOS — Cara Pakai

1. Buka tab **INFO** → klik **📋 COPY GW → DDOS TARGET**
   (atau isi IP manual di tab DDOS)
2. Buka tab **DDOS**
3. Pilih mode:
   - **UDP FLOOD** — saturasi bandwidth paling agresif
   - **TCP FLOOD** — exhausts connection table router
   - **ICMP FLOOD** — ping storm (butuh raw socket / root untuk paling efektif)
   - **HTTP FLOOD** — flood web interface router (port 80/8080)
   - **SLOWLORIS** — connection exhaustion, 50 socket lambat
   - **COMBO ALL** — UDP + TCP + HTTP sekaligus
4. Atur **THREADS** (lebih banyak = lebih agresif, drain baterai lebih cepat)
5. Atur **PAYLOAD B** (UDP payload size, max 65000 byte)
6. Tap **☠ LAUNCH DDOS**
7. Lihat PPS counter di stat bar kanan atas

**Efek:** Router/AP kehabisan resource → internet semua user di jaringan itu
lambat / timeout / putus total tergantung kekuatan router.

---

### Tab SPAM — Mode Baru v6.0

| Mode | Cara Kerja | Root? |
|------|-----------|-------|
| DISCO | disconnect hp sendiri berulang | ✗ |
| AUTH | reconnect burst | ✗ |
| DEAUTH | aireplay-ng --deauth (count slider) | ✓ |
| MDK4 | mdk4 deauth all clients | ✓ |
| BEACON | mdk4 beacon flood (SSID spam) | ✓ |

---

### ROOT Tools Baru v6.0

| Tool | Fungsi |
|------|--------|
| Monitor Mode | airmon-ng start wlan0 |
| Channel Hopper | iwconfig hop 1-13 tiap 300ms |
| Airodump Scan | airodump-ng 10s ke /tmp/rdump-01.csv |
| MDK4 Beacon Flood | mdk4 b — ratusan fake SSID per detik |
| MDK4 Deauth Storm | mdk4 d — keluarkan semua klien |
| PMKID Harvest | hcxdumptool → /tmp/pmkid.pcapng |

---

### Install Tools (Root)

```bash
# Termux dengan root
pkg install root-repo
pkg install aircrack-ng mdk4 hcxdumptool wireless-tools

# Kali NetHunter
apt install aircrack-ng mdk4 hcxdumptool
```

---

### Build APK

```bash
chmod +x setup_build.sh && ./setup_build.sh
# atau CachyOS
chmod +x setup_cachyos.sh && ./setup_cachyos.sh
```

---

### Kompatibilitas

- Android 6.0+ (API 23)
- arm64-v8a + armeabi-v7a
- DDOS engine: non-root, socket biasa (UDP/TCP/HTTP)
- ICMP flood: lebih efektif dengan root (raw socket)
- MDK4/deauth/beacon: butuh root + monitor mode

---

*dibuat oleh NETACT dan BOWOgaming — v6.0 DDOS Edition*
