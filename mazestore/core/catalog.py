"""Curated shop-window text for the packages in [mazelinux].

The repo db only carries a one-line English `pkgdesc`. This table adds what a
store needs on top: a display name, a category and a short pitch in both
languages. It is *only* presentation — which packages exist, their versions and
sizes always come from the db, so a package published tomorrow appears in the
store without touching this file (under "Other", with its pkgdesc).
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = ["all", "privacy", "security", "ai", "crypto", "desktop", "system", "other"]


@dataclass(frozen=True)
class Entry:
    title: str
    category: str
    tagline_en: str
    tagline_tr: str
    featured: bool = False
    # A component the rest of Maze Linux leans on. The store still lets you
    # remove it — it is your machine — but asks twice.
    core: bool = False


CATALOG: dict[str, Entry] = {
    # ── privacy ──────────────────────────────────────────────────────────────
    "entropy-shield": Entry(
        "Entropy Shield", "privacy",
        "Tor, DNSCrypt, I2P and onion services from one switchboard.",
        "Tor, DNSCrypt, I2P ve onion servisleri tek panelden.", featured=True),
    "maze-cloak": Entry(
        "Maze Cloak", "privacy",
        "Randomise your MAC address, per network or on a schedule.",
        "MAC adresini ağa göre ya da zamanlanmış olarak rastgeleleştir.", featured=True),
    "haze": Entry(
        "Haze", "privacy",
        "Anonymous, end-to-end encrypted P2P chat over Tor.",
        "Tor üzerinden anonim, uçtan uca şifreli P2P sohbet.", featured=True),
    "hazedrop": Entry(
        "HazeDrop", "privacy",
        "Send files anonymously over Tor with the Haze protocol.",
        "Haze protokolüyle Tor üzerinden anonim dosya gönder."),
    "gaze": Entry(
        "Gaze", "privacy",
        "Privacy test suite: IP, DNS, IPv6 and WebRTC leaks at a glance.",
        "Gizlilik testi: IP, DNS, IPv6 ve WebRTC sızıntılarını gör."),
    "maze-connect": Entry(
        "Maze Connect", "privacy",
        "Pair your phone over the LAN with pinned mutual TLS.",
        "Telefonunu yerel ağda, sabitlenmiş karşılıklı TLS ile eşle.", featured=True),

    # ── security ─────────────────────────────────────────────────────────────
    "maze-guard": Entry(
        "Maze Guard", "security",
        "Public Wi-Fi watchdog: MITM detection and firewall control.",
        "Halka açık Wi-Fi bekçisi: MITM tespiti ve güvenlik duvarı.", featured=True),
    "qlam": Entry(
        "Qlam", "security",
        "Warn-first antivirus with on-access protection for your files.",
        "Önce uyaran antivirüs: dosyaların için erişim anında koruma.", featured=True),
    "sentinai": Entry(
        "SentinAI", "security",
        "AI cybersecurity assistant with OSINT tooling.",
        "OSINT araçlarıyla yapay zekâ destekli siber güvenlik asistanı."),
    "maze-hardening": Entry(
        "Maze Hardening", "system",
        "Kernel and network hardening defaults.",
        "Çekirdek ve ağ sertleştirme varsayılanları.", core=True),
    "maze-secureboot": Entry(
        "Maze Secure Boot", "system",
        "UKI rebuilds, MOK signing and a boot-chain check before reboot.",
        "UKI yeniden oluşturma, MOK imzalama ve yeniden başlatma öncesi zincir kontrolü.",
        core=True),
    "maze-snapshots": Entry(
        "Maze Snapshots", "system",
        "Automatic btrfs snapshots — every pacman transaction can be rolled back.",
        "Otomatik btrfs anlık görüntüleri — her pacman işlemi geri alınabilir."),

    # ── AI ───────────────────────────────────────────────────────────────────
    "maze-ai": Entry(
        "Maze AI", "ai",
        "Agentic assistant on local models via Ollama.",
        "Ollama ile yerel modellerde çalışan ajan asistan.", featured=True),
    "linux-chan-ai": Entry(
        "Linux-Chan AI", "ai",
        "A Linux-themed chat companion with voice.",
        "Sesli, Linux temalı sohbet arkadaşı."),
    "ai-watermark-remover": Entry(
        "AI Watermark Remover", "ai",
        "Rewrite comments with a local model to break LLM text watermarks.",
        "Yorumları yerel modelle yeniden yazarak LLM filigranlarını kır."),

    # ── crypto ───────────────────────────────────────────────────────────────
    "maze-crypto": Entry(
        "Maze Crypto", "crypto",
        "Read-only market, portfolio and DCA tracker.",
        "Salt-okunur piyasa, portföy ve DCA takipçisi.", featured=True),
    "ledger-live": Entry(
        "Ledger Live", "crypto",
        "Manage your Ledger hardware wallet.",
        "Ledger donanım cüzdanını yönet."),
    "ledger-udev": Entry(
        "Ledger udev rules", "crypto",
        "Lets Linux talk to Ledger devices over USB.",
        "Linux'un Ledger cihazlarıyla USB üzerinden konuşmasını sağlar."),

    # ── desktop ──────────────────────────────────────────────────────────────
    "maze-wallpaper": Entry(
        "Maze Wallpaper", "desktop",
        "Static, live video/GIF and now-playing wallpapers.",
        "Statik, canlı video/GIF ve çalan şarkı duvar kâğıtları.", featured=True),
    "plasma6-applets-ai-usage": Entry(
        "AI Usage widget", "desktop",
        "Plasma widget for Claude, Codex, Gemini and Copilot plan limits.",
        "Claude, Codex, Gemini ve Copilot limitleri için Plasma widget'ı."),
    "plasma6-applets-coin-tracker": Entry(
        "Coin Tracker widget", "desktop",
        "Live crypto prices and 7-day charts on your panel.",
        "Panelinde canlı kripto fiyatları ve 7 günlük grafikler."),
    "maze-gaming": Entry(
        "Maze Gaming", "desktop",
        "Gaming defaults: shader caches, GameMode, ntsync, MangoHud.",
        "Oyun ayarları: shader önbelleği, GameMode, ntsync, MangoHud."),
    "maze-plasma-config": Entry(
        "Maze Plasma Config", "desktop",
        "The Maze KDE Plasma layout, widgets and defaults.",
        "Maze KDE Plasma düzeni, widget'ları ve varsayılanları.", core=True),
    "maze-branding": Entry(
        "Maze Branding", "desktop",
        "Boot splash, login theme, wallpapers and logos.",
        "Açılış ekranı, giriş teması, duvar kâğıtları ve logolar.", core=True),

    # ── system ───────────────────────────────────────────────────────────────
    "maze-tools": Entry(
        "Maze Tools", "system",
        "Control Center, Welcome, system doctor and the Maze CLI utilities.",
        "Kontrol Merkezi, Hoş Geldin, sistem doktoru ve Maze CLI araçları.",
        core=True),
    "maze-meta": Entry(
        "Maze Linux (full set)", "system",
        "Pulls in every default Maze package.",
        "Tüm varsayılan Maze paketlerini kurar.", core=True),
    "paru": Entry(
        "paru", "system",
        "Feature-packed AUR helper.",
        "Özellik dolu AUR yardımcısı."),
}

# Never shown: debug symbols, and plumbing that only exists to be a dependency
# of something else (installing the keyring or the shared venv by hand from a
# shop window does nothing useful; the installer only makes sense on the ISO).
# The store itself is listed so it cannot offer to remove itself.
HIDDEN = {"mazelinux-keyring", "maze-python", "maze-installer", "maze-store"}


def is_hidden(name: str) -> bool:
    return name in HIDDEN or name.endswith("-debug")


def entry_for(name: str, pkgdesc: str = "") -> Entry:
    e = CATALOG.get(name)
    if e is not None:
        return e
    title = name.replace("-", " ").title() if name.startswith("maze-") else name
    return Entry(title, "other", pkgdesc, pkgdesc)
