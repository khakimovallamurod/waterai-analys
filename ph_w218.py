"""
PH-W218 (WiFi smart online 8 in 1 tester) qurilmasi integratsiyasi.

Qurilmaga lokal tarmoq (LAN) orqali Tuya protokoli (tinytuya) bilan ulanadi,
fon oqimida (thread) ma'lumotlarni muntazam o'qiydi, jonli tarixni saqlaydi va
model o'qitish uchun CSV dataset yig'adi.

Sozlamalar .env faylidan olinadi:
    TUYA_DEVICE_ID, TUYA_LOCAL_KEY, TUYA_DEVICE_IP, TUYA_VERSION (3.5), POLL_INTERVAL (2)
"""
import csv
import errno
import ipaddress
import logging
import os
import socket
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover
    dotenv_values = None

try:
    import tinytuya
except ImportError:  # pragma: no cover - kutubxona o'rnatilmagan bo'lsa
    tinytuya = None

import ai_engine

logger = logging.getLogger(__name__)

DEVICE_NAME = "PH-W218 · WiFi smart online 8 in 1 tester"

# Tuya DPS kodlari -> parametrlar. scale: xom qiymat shu songa bo'linadi.
SENSORS: Dict[str, Dict[str, Any]] = {
    "temperature": {"dp": "8", "scale": 10, "unit": "°C", "name": "Harorat", "decimals": 1},
    "ph": {"dp": "106", "scale": 100, "unit": "pH", "name": "pH", "decimals": 2},
    "tds": {"dp": "111", "scale": 1, "unit": "ppm", "name": "TDS", "decimals": 0},
    "ec": {"dp": "116", "scale": 1, "unit": "µS/cm", "name": "EC", "decimals": 0},
    "salinity": {"dp": "121", "scale": 1, "unit": "ppm", "name": "Sho'rlanish", "decimals": 0},
    "sg": {"dp": "126", "scale": 1, "unit": "S.G", "name": "Solishtirma og'irlik (S.G)", "decimals": 0},
    "orp": {"dp": "131", "scale": 1, "unit": "mV", "name": "ORP", "decimals": 0},
    "cf": {"dp": "136", "scale": 1, "unit": "CF", "name": "CF", "decimals": 0},
    "humidity": {"dp": "141", "scale": 1, "unit": "%", "name": "Namlik", "decimals": 0},
}

MAX_HISTORY = 1800          # ~1 soat (2 soniyalik interval bilan)
OFFLINE_AFTER_FAILS = 3     # ketma-ket xatolardan keyin "qayta ulanmoqda" holati
RECREATE_AFTER_FAILS = 5    # ketma-ket xatolardan keyin ulanish obyektini qayta yaratish

DATASET_DIR = os.getenv("DATASET_DIR", "datasets")
DATASET_PATH = os.path.join(DATASET_DIR, "ph_w218_dataset.csv")

DATASET_FIELDS = [
    "timestamp", "session_id", "sample_name", "source_type", "location", "label",
    "temperature", "ph", "tds", "ec", "salinity", "orp", "sg", "cf", "humidity",
    "quality_status", "quality_score", "trigger",
]

# Dataset yozuvi uchun o'zgarish chegaralari: (absolyut, nisbiy).
# Yozuv faqat birorta asosiy parametr max(abs, nisbiy * |oldingi|) dan ko'proq o'zgarganda olinadi.
CHANGE_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    "temperature": (0.2, 0.0),
    "ph": (0.03, 0.0),
    "tds": (2.0, 0.01),
    "ec": (4.0, 0.01),
    "salinity": (2.0, 0.01),
    "orp": (3.0, 0.0),
}


def _env_config() -> Dict[str, Any]:
    """Qurilma sozlamalari: avval muhit o'zgaruvchilari, so'ng .env fayli (faqat TUYA kalitlari)."""
    file_vals = dotenv_values(".env") if dotenv_values else {}

    def get(name: str, default: str = "") -> str:
        return os.getenv(name) or file_vals.get(name) or default

    return {
        "device_id": get("TUYA_DEVICE_ID").strip(),
        "local_key": get("TUYA_LOCAL_KEY"),
        "ip": get("TUYA_DEVICE_IP").strip(),
        "version": float(get("TUYA_VERSION", "3.5")),
        "poll_interval": max(1.0, float(get("POLL_INTERVAL", "2"))),
    }



TUYA_PORT = 6668
AUTO_PROBE_SEC = 15       # avtomatik ulanish: ma'lum IP ni shuncha soniyada bir tekshirish
AUTO_SCAN_SEC = 90        # avtomatik ulanish: tarmoqni qidirish (scan) oralig'i


def _local_ip_for(target: str) -> Optional[str]:
    """Operatsion tizim `target` ga yetish uchun qaysi o'z IP sini ishlatishini aniqlaydi (paket yuborilmaydi)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect((target, TUYA_PORT))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def _all_local_ips() -> List[str]:
    ips: List[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def _netmask_of(ip: Optional[str]) -> Optional[str]:
    """psutil o'rnatilgan bo'lsa, shu IP ning haqiqiy tarmoq niqobini qaytaradi."""
    if not ip:
        return None
    try:
        import psutil  # ixtiyoriy
        for addrs in psutil.net_if_addrs().values():
            for a in addrs:
                if a.family == socket.AF_INET and a.address == ip:
                    return a.netmask
    except Exception:
        pass
    return None


def _same_network(local_ip: str, device_ip: str) -> Tuple[Optional[bool], str]:
    """Server va qurilma bitta tarmoqdami? (natija, tushuntirish)."""
    try:
        mask = _netmask_of(local_ip)
        if mask:
            net = ipaddress.ip_network(f"{local_ip}/{mask}", strict=False)
            return ipaddress.ip_address(device_ip) in net, f"{net}, niqob {mask}"
        # Niqob noma'lum: faqat taxmin (aniq "yo'q" deb bo'lmaydi)
        net = ipaddress.ip_network(f"{local_ip}/24", strict=False)
        if ipaddress.ip_address(device_ip) in net:
            return True, f"{net}, taxminiy"
        return None, f"niqob aniqlanmadi, taxminan {net}"
    except Exception:
        return None, ""


def _tcp_probe(ip: str, port: int = TUYA_PORT, timeout: float = 2.0) -> Tuple[str, str]:
    """('open'|'refused'|'unreachable'|'timeout'|'error', xabar)"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        code = s.connect_ex((ip, port))
    except socket.timeout:
        return "timeout", "javob kelmadi"
    except Exception as e:
        return "error", str(e)
    finally:
        s.close()
    if code == 0:
        return "open", "port ochiq"
    refused = {errno.ECONNREFUSED, 10061}
    unreachable = {errno.EHOSTUNREACH, errno.ENETUNREACH, errno.EHOSTDOWN, 10051, 10065}
    timedout = {errno.ETIMEDOUT, errno.EAGAIN, 10060}
    if code in refused:
        return "refused", "qurilma javob berdi, lekin port yopiq"
    if code in unreachable:
        return "unreachable", "qurilmaga yo'l yo'q (tarmoqda ko'rinmayapti)"
    if code in timedout:
        return "timeout", "javob kelmadi (vaqt tugadi)"
    return "error", f"xato kodi {code}"


def parse_dps(dps: Dict[str, Any]) -> Dict[str, float]:
    """Tuya DPS lug'atini haqiqiy qiymatlarga aylantirish."""
    values = {}
    for key, meta in SENSORS.items():
        raw = dps.get(meta["dp"], 0)
        try:
            raw = float(raw)
        except (TypeError, ValueError):
            raw = 0.0
        values[key] = round(raw / meta["scale"], 3)
    return values


def is_reading_valid(values: Dict[str, float]) -> bool:
    """Datchik suvga botirilmagan yoki noto'g'ri o'qish holatlarini aniqlash."""
    if not (0.0 < values.get("ph", 0) <= 14.0):
        return False
    if values.get("tds", 0) == 0 and values.get("ec", 0) == 0:
        return False
    return True


def _changed(a: Dict[str, float], b: Dict[str, float]) -> List[str]:
    """a va b o'rtasida chegaradan oshgan o'zgarishga ega parametrlar ro'yxati."""
    out = []
    for key, (abs_t, rel_t) in CHANGE_THRESHOLDS.items():
        prev, cur = b.get(key, 0.0), a.get(key, 0.0)
        if abs(cur - prev) >= max(abs_t, rel_t * abs(prev)):
            out.append(key)
    return out


class DatasetRecorder:
    """
    Qurilmadan kelgan o'lchovlarni CSV datasetga yozadi.

    Mantiq (takroriy va shovqinli qatorlarsiz toza dataset uchun):
      1. Noto'g'ri o'qishlar (pH 0 yoki datchik havoda) tashlab yuboriladi.
      2. Barqarorlik: joriy o'qish oldingi o'qishga yaqin bo'lishi kerak (sakrash/o'tish
         jarayonidagi qiymatlar yozilmaydi).
      3. O'zgarish: oxirgi yozilgan qatordan kamida bitta asosiy parametr chegaradan
         ko'proq farq qilsa yoziladi.
      4. Ixtiyoriy "heartbeat": o'zgarish bo'lmasa ham har N soniyada bitta qator.
    """

    def __init__(self, path: str = DATASET_PATH):
        self.path = path
        self._lock = threading.Lock()
        self.recording = False
        self.session_id: Optional[str] = None
        self.meta: Dict[str, str] = {}
        self.heartbeat_sec = 0
        self.started_at: Optional[str] = None
        self.session_rows = 0
        self.skipped = 0
        self.last_row: Optional[Dict[str, Any]] = None
        self._last_recorded: Optional[Dict[str, float]] = None
        self._last_recorded_ts = 0.0
        self._prev_reading: Optional[Dict[str, float]] = None
        self.recent: deque = deque(maxlen=15)
        self.total_rows = self._count_rows()

    def _count_rows(self) -> int:
        if not os.path.exists(self.path):
            return 0
        with open(self.path, "r", encoding="utf-8") as f:
            return max(sum(1 for _ in f) - 1, 0)

    def start(self, sample_name: str, source_type: str, location: str, label: str, heartbeat_sec: int = 0):
        with self._lock:
            self.recording = True
            self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
            self.meta = {
                "sample_name": (sample_name or "PH-W218 namunasi").strip(),
                "source_type": (source_type or "Boshqa").strip(),
                "location": (location or "").strip(),
                "label": (label or "").strip(),
            }
            self.heartbeat_sec = max(0, int(heartbeat_sec or 0))
            self.started_at = datetime.now().isoformat(timespec="seconds")
            self.session_rows = 0
            self.skipped = 0
            self._last_recorded = None
            self._last_recorded_ts = 0.0
            self._prev_reading = None

    def stop(self):
        with self._lock:
            self.recording = False

    def clear(self):
        with self._lock:
            if os.path.exists(self.path):
                os.remove(self.path)
            self.total_rows = 0
            self.session_rows = 0
            self.last_row = None
            self.recent.clear()

    def feed(self, values: Dict[str, float], timestamp: str):
        """Har bir yangi o'qishda chaqiriladi. Kerak bo'lsa datasetga qator yozadi."""
        with self._lock:
            if not self.recording:
                return
            if not is_reading_valid(values):
                self.skipped += 1
                self._prev_reading = None
                return

            prev = self._prev_reading
            self._prev_reading = dict(values)
            # Barqarorlik: kamida 2 ketma-ket o'xshash o'qish bo'lishi kerak
            if prev is None or _changed(values, prev):
                return

            now = time.monotonic()
            if self._last_recorded is None:
                trigger = "first"
            else:
                changed = _changed(values, self._last_recorded)
                if changed:
                    trigger = ",".join(changed)
                elif self.heartbeat_sec and now - self._last_recorded_ts >= self.heartbeat_sec:
                    trigger = "heartbeat"
                else:
                    return

            result = ai_engine.analyze_device_sample({**values, "source_type": self.meta["source_type"]})
            row = {
                "timestamp": timestamp,
                "session_id": self.session_id,
                **self.meta,
                **{k: values.get(k, 0) for k in SENSORS},
                "quality_status": result["status"],
                "quality_score": result["quality_score"],
                "trigger": trigger,
            }
            self._write(row)
            self._last_recorded = dict(values)
            self._last_recorded_ts = now
            self.session_rows += 1
            self.total_rows += 1
            self.last_row = row
            self.recent.appendleft(row)

    def _write(self, row: Dict[str, Any]):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        new_file = not os.path.exists(self.path) or os.path.getsize(self.path) == 0
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=DATASET_FIELDS)
            if new_file:
                writer.writeheader()
            writer.writerow(row)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "recording": self.recording,
                "session_id": self.session_id,
                "meta": self.meta,
                "heartbeat_sec": self.heartbeat_sec,
                "started_at": self.started_at,
                "session_rows": self.session_rows,
                "skipped": self.skipped,
                "total_rows": self.total_rows,
                "last_row": self.last_row,
                "recent": list(self.recent),
            }


class PHW218Service:
    """Qurilma bilan ulanish, fon o'qish oqimi va jonli holatni boshqaradi."""

    def __init__(self):
        self._lock = threading.RLock()
        self._device = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.config = _env_config()
        self.state = "disconnected"  # disconnected | connecting | online | reconnecting
        self.error: Optional[str] = None
        self.last_dps: Dict[str, Any] = {}
        self.values: Optional[Dict[str, float]] = None
        self.last_update: Optional[str] = None
        self.history: deque = deque(maxlen=MAX_HISTORY)
        self.recorder = DatasetRecorder()
        self._fails = 0
        self._manual_off = False          # foydalanuvchi o'zi "Uzish" bosgan bo'lsa, avto-ulanish to'xtaydi
        self._watch_thread: Optional[threading.Thread] = None
        self._watch_stop = threading.Event()
        self.auto_status = "off"          # off | waiting | scanning | connecting | connected
        self.last_diag: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------ helpers
    def is_configured(self) -> bool:
        c = self.config
        return bool(c["device_id"] and c["local_key"])

    def _make_device(self):
        c = self.config
        # Ishlaydigan ph-w218-visualization loyihasidagi kabi: tinytuya standart
        # taymaut va qayta urinishlari bilan (v3.5 sessiya kaliti kelishuvi sekinroq).
        dev = tinytuya.Device(
            dev_id=c["device_id"],
            address=c["ip"],
            local_key=c["local_key"],
            version=c["version"],
        )
        dev.set_socketPersistent(True)
        return dev

    def _discover_ip(self) -> bool:
        """Qurilma boshqa tarmoqda/IP o'zgargan bo'lsa, lokal tarmoqda uni ID bo'yicha qidiradi."""
        try:
            found = tinytuya.find_device(self.config["device_id"])
        except Exception as e:  # pragma: no cover
            logger.warning("PH-W218 qidirishda xato: %s", e)
            return False
        ip = (found or {}).get("ip")
        if not ip:
            return False
        if ip != self.config["ip"]:
            logger.info("PH-W218 yangi IP topildi: %s (oldin: %s)", ip, self.config["ip"])
        self.config["ip"] = ip
        ver = (found or {}).get("version")
        try:
            if ver:
                self.config["version"] = float(ver)
        except (TypeError, ValueError):
            pass
        return True

    # ------------------------------------------------------------------ diagnostika
    def diagnose(self, deep: bool = False) -> Dict[str, Any]:
        """
        Server va qurilma bitta tarmoqdami, qurilma ko'rinyaptimi, nima to'sqinlik qilyapti.
        deep=True bo'lsa tarmoqda ID bo'yicha qidiruv (scan) ham bajariladi (~20 soniya).
        """
        cfg = self.config = _env_config()
        checks: List[Dict[str, str]] = []

        def add(title: str, status: str, detail: str):
            checks.append({"title": title, "status": status, "detail": detail})  # status: ok | warn | fail | info

        dev_ip = cfg["ip"]
        local_ips = _all_local_ips()
        route_ip = _local_ip_for(dev_ip) if dev_ip and dev_ip.lower() != "auto" else None
        if route_ip and route_ip not in local_ips:
            local_ips.insert(0, route_ip)
        add("Server kompyuteri IP manzillari", "info", ", ".join(local_ips) or "aniqlanmadi")

        if tinytuya is None:
            add("tinytuya kutubxonasi", "fail", "o'rnatilmagan: pip install tinytuya")
        if not cfg["device_id"] or not cfg["local_key"]:
            add(".env sozlamalari", "fail", "TUYA_DEVICE_ID yoki TUYA_LOCAL_KEY yo'q")
        else:
            add(".env sozlamalari", "ok", f"qurilma ID va kalit bor, versiya {cfg['version']}")

        verdict, level = "", "info"
        reach = "unknown"
        if dev_ip and dev_ip.lower() != "auto":
            local = _local_ip_for(dev_ip)
            if local:
                same, note = _same_network(local, dev_ip)
                if same is True:
                    add("Bitta tarmoqmi?", "ok", f"Ha: server {local} va qurilma {dev_ip} bir tarmoqda ({note})")
                elif same is False:
                    add("Bitta tarmoqmi?", "fail", f"Yo'q: server {local}, qurilma {dev_ip} ({note}). Qurilma va kompyuter bitta Wi-Fi/routerda bo'lishi kerak")
                else:
                    add("Bitta tarmoqmi?", "warn", f"Server {local}, qurilma {dev_ip}: aniqlab bo'lmadi")
            else:
                add("Bitta tarmoqmi?", "fail", f"{dev_ip} manziliga yo'nalish topilmadi (kompyuter tarmoqqa ulanmagan bo'lishi mumkin)")
            reach, msg = _tcp_probe(dev_ip)
            st = {"open": "ok", "refused": "warn"}.get(reach, "fail")
            add(f"Qurilma {dev_ip}:{TUYA_PORT}", st, msg)
        else:
            add("Qurilma IP si", "info", ".env da ko'rsatilmagan, avtomatik qidiriladi")

        found = None
        if deep and tinytuya is not None and cfg["device_id"]:
            try:
                found = tinytuya.find_device(cfg["device_id"])
            except Exception as e:  # pragma: no cover
                add("Tarmoq qidiruvi (scan)", "warn", f"xato: {e}")
            if found and found.get("ip"):
                add("Tarmoq qidiruvi (scan)", "ok", f"Qurilma topildi: {found['ip']} (versiya {found.get('version', '?')})")
                if dev_ip and found["ip"] != dev_ip:
                    add("IP o'zgargan", "warn", f".env da {dev_ip}, hozir {found['ip']}. Dastur yangi manzilga o'zi ulanadi")
                reach = "found"
            elif found is not None or not any(c["title"].startswith("Tarmoq qidiruvi") for c in checks):
                add("Tarmoq qidiruvi (scan)", "fail", "Qurilma shu tarmoqda topilmadi (o'chiq yoki boshqa tarmoqda)")

        with self._lock:
            state, err = self.state, self.error
        if state == "online":
            verdict, level = "Qurilma ulangan va ma'lumot kelyapti.", "ok"
        elif reach == "open":
            verdict, level = ("Qurilma tarmoqda ko'rinyapti. Ulanmayotgan bo'lsa: Tuya qurilma bir vaqtda faqat BITTA lokal ulanishni qabul qiladi. "
                              "Boshqa kompyuterdagi dastur (masalan ph-w218-visualization), telefondagi Tuya/Smart Life ilovasi yoki ikkinchi WaterAI nusxasi "
                              "ulanib turgan bo'lsa, ularni yoping. Yana: kalit (TUYA_LOCAL_KEY) va versiya to'g'riligini tekshiring."), "warn"
        elif reach == "refused":
            verdict, level = "Qurilma tarmoqda bor, lekin 6668 port yopiq: boshqa dastur ulanishni band qilgan bo'lishi mumkin. Boshqa ulanishlarni yoping.", "warn"
        elif reach == "found":
            verdict, level = "Qurilma boshqa IP da topildi, ulanishga urinib ko'ring.", "warn"
        elif reach in ("unreachable", "timeout"):
            verdict, level = ("Qurilma ko'rinmayapti: u o'chiq, boshqa Wi-Fi'ga ulangan yoki IP manzili o'zgargan bo'lishi mumkin. "
                              "Qurilmani yoqib, kompyuter bilan BIR tarmoqqa ulang."), "fail"
        else:
            verdict, level = "Qurilma tarmoqdan qidirilmoqda. Qurilmani yoqib, kompyuter bilan bir tarmoqqa ulang.", "warn"
        if err and state != "online":
            add("Oxirgi xato", "info", str(err))

        result = {
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "level": level, "verdict": verdict, "checks": checks,
            "server_ips": local_ips, "device_ip": dev_ip, "deep": deep,
        }
        self.last_diag = result
        return result

    def _short_reason(self, err: Optional[str]) -> str:
        """Ulanish xatosiga qisqa, tushunarli izoh qo'shadi (tezkor tekshiruv, scan'siz)."""
        d = self.diagnose(deep=False)
        reason = err or "Noma'lum xato"
        return f"{reason}. {d['verdict']}"

    # ------------------------------------------------------------------ avto-ulanish
    def start_watcher(self):
        """Fon oqimi: qurilma paydo bo'lishi bilan o'zi ulanadi (foydalanuvchi "Uzish" bosmagan bo'lsa)."""
        if os.getenv("AUTO_CONNECT", "1").strip().lower() in ("0", "false", "no", "off"):
            self.auto_status = "off"
            return
        if self._watch_thread and self._watch_thread.is_alive():
            return
        self._watch_stop.clear()
        self._watch_thread = threading.Thread(target=self._watch_loop, name="ph-w218-watcher", daemon=True)
        self._watch_thread.start()

    def stop_watcher(self):
        self._watch_stop.set()
        t = self._watch_thread
        if t and t.is_alive():
            t.join(timeout=3)
        self._watch_thread = None
        self.auto_status = "off"

    def _watch_loop(self):
        last_scan = 0.0
        while not self._watch_stop.wait(AUTO_PROBE_SEC):
            try:
                if self._manual_off or self.state in ("online", "reconnecting", "connecting"):
                    self.auto_status = "connected" if self.state in ("online", "reconnecting") else "waiting"
                    continue
                self.config = _env_config()
                if not self.is_configured() or tinytuya is None:
                    self.auto_status = "off"
                    continue
                self.auto_status = "waiting"
                ip = self.config["ip"]
                try_connect = False
                if ip and ip.lower() != "auto":
                    status, _ = _tcp_probe(ip, timeout=1.5)
                    try_connect = status == "open"
                if not try_connect and time.monotonic() - last_scan >= AUTO_SCAN_SEC:
                    last_scan = time.monotonic()
                    self.auto_status = "scanning"
                    try_connect = self._discover_ip()
                if try_connect:
                    self.auto_status = "connecting"
                    ok, msg = self.connect()
                    logger.info("PH-W218 avto-ulanish: %s", msg)
                    self.auto_status = "connected" if ok else "waiting"
            except Exception as e:  # pragma: no cover
                logger.warning("PH-W218 avto-ulanish xatosi: %s", e)

    def _close_device(self):
        if self._device is not None:
            try:
                self._device.close()
            except Exception:
                pass
            self._device = None

    def _read(self) -> Tuple[Optional[Dict[str, float]], Optional[str]]:
        try:
            data = self._device.status()
        except Exception as e:
            return None, str(e)
        if data and "dps" in data:
            # Tuya qurilmalari qisman yangilanish yuborishi mumkin
            self.last_dps.update(data["dps"])
            return parse_dps(self.last_dps), None
        if data and "Error" in data:
            return None, str(data["Error"])
        return None, "Qurilmadan ma'lumot kelmadi"

    def _store(self, values: Dict[str, float]):
        ts = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            self.values = values
            self.last_update = ts
            self.state = "online"
            self.error = None
            self.history.append({"timestamp": ts, **values})
        self.recorder.feed(values, ts)

    # ------------------------------------------------------------------ public
    def connect(self) -> Tuple[bool, str]:
        with self._lock:
            if self.state in ("online", "reconnecting") and self._thread and self._thread.is_alive():
                return True, "Qurilma allaqachon ulangan"
            self.config = _env_config()
            if tinytuya is None:
                self.error = "tinytuya kutubxonasi o'rnatilmagan (pip install tinytuya)"
                return False, self.error
            if not self.is_configured():
                self.error = ".env faylida TUYA_DEVICE_ID, TUYA_LOCAL_KEY, TUYA_DEVICE_IP sozlanmagan"
                return False, self.error
            self.state = "connecting"
            self.last_dps = {}
            self._manual_off = False

        values, err = None, None
        if self.config["ip"] and self.config["ip"].lower() != "auto":
            try:
                self._device = self._make_device()
                values, err = self._read()
            except Exception as e:
                values, err = None, str(e)

        if values is None:
            # IP noto'g'ri/o'zgargan yoki .env da yo'q: qurilmani tarmoqdan avtomatik qidiramiz
            self._close_device()
            if self._discover_ip():
                try:
                    self._device = self._make_device()
                    values, err = self._read()
                except Exception as e:
                    values, err = None, str(e)
            elif not err:
                err = "Qurilma tarmoqda topilmadi"

        if values is None and err and ("key or version" in err or "914" in err):
            # Port ochiq, lekin kalit/versiya mos kelmadi: boshqa protokol versiyalarini sinaymiz
            orig = self.config["version"]
            for ver in (3.5, 3.4, 3.3, 3.2, 3.1):
                if ver == orig:
                    continue
                self._close_device()
                self.config["version"] = ver
                try:
                    self._device = self._make_device()
                    values, _ = self._read()
                except Exception:
                    values = None
                if values is not None:
                    logger.info("PH-W218 versiya %s bilan ulandi (.env da %s edi)", ver, orig)
                    err = None
                    break
            else:
                self.config["version"] = orig
                err = f"{err} (versiyalar 3.1-3.5 sinab ko'rildi: TUYA_LOCAL_KEY noto'g'ri yoki eskirgan)"

        if values is None:
            self._close_device()
            with self._lock:
                self.state = "disconnected"
                self.error = err
            logger.warning("PH-W218 ulanmadi: %s", err)
            return False, self._short_reason(err)

        self._store(values)
        self._fails = 0
        self._stop.clear()
        self._thread = threading.Thread(target=self._poll_loop, name="ph-w218-poller", daemon=True)
        self._thread.start()
        logger.info("PH-W218 ulandi (%s)", self.config["ip"])
        return True, "Qurilmaga muvaffaqiyatli ulandi"

    def disconnect(self, manual: bool = False):
        if manual:
            self._manual_off = True
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._thread = None
        self._close_device()
        self.recorder.stop()
        with self._lock:
            self.state = "disconnected"
            self.error = None

    def _poll_loop(self):
        while not self._stop.wait(self.config["poll_interval"]):
            try:
                if self._device is None:
                    self._device = self._make_device()
                values, err = self._read()
            except Exception as e:
                values, err = None, str(e)

            if values is not None:
                self._fails = 0
                self._store(values)
                continue

            self._fails += 1
            logger.warning("PH-W218 o'qish xatosi (%d): %s", self._fails, err)
            with self._lock:
                self.error = err
                if self._fails >= OFFLINE_AFTER_FAILS:
                    self.state = "reconnecting"
            if self._fails % RECREATE_AFTER_FAILS == 0:
                self._close_device()

    def get_history(self, limit: int = MAX_HISTORY) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.history)[-limit:]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            values = None
            if self.values is not None:
                values = {
                    key: {
                        "value": self.values[key],
                        "unit": meta["unit"],
                        "name": meta["name"],
                        "decimals": meta["decimals"],
                    }
                    for key, meta in SENSORS.items()
                }
            return {
                "configured": self.is_configured(),
                "state": self.state,
                "online": self.state == "online",
                "error": self.error,
                "last_update": self.last_update,
                "reading_valid": is_reading_valid(self.values) if self.values else False,
                "device": {"name": DEVICE_NAME, "ip": self.config["ip"]},
                "auto_connect": self.auto_status,
                "manual_off": self._manual_off,
                "values": values,
                "recorder": self.recorder.snapshot(),
            }


ph_service = PHW218Service()
