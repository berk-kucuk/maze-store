"""English and Turkish strings. `t()` falls back to English, then to the key."""
from __future__ import annotations

from PyQt6.QtCore import QLocale

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "search": "Search apps",
        "tip_minimize": "Minimize",
        "tip_maximize": "Maximize / Restore",
        "tip_close": "Close",
        "notify_title": "Update alerts",
        "notify_hint": "Checks every 6 hours",
        "nav_browse": "BROWSE",
        "nav_library": "LIBRARY",
        "cat_all": "Discover",
        "cat_privacy": "Privacy",
        "cat_security": "Security",
        "cat_ai": "AI",
        "cat_crypto": "Crypto",
        "cat_desktop": "Desktop",
        "cat_system": "System",
        "cat_other": "Other",
        "lib_installed": "Installed",
        "lib_updates": "Updates",
        "hero_title": "Every Maze app,\nin one place.",
        "hero_sub": "Signed packages from the [mazelinux] repository. Installs run "
                    "in a terminal and sudo asks for your password — the store "
                    "itself never has root.",
        "sec_featured": "Featured",
        "sec_all": "All apps",
        "sec_results": "Results",
        "sec_featured_sub": "Built for Maze Linux, by the Maze team.",
        "sec_all_sub": "Everything else in the repository.",
        "hero_eyebrow": "MAZE LINUX",
        "count_apps": "{n} apps",
        "chip_installed": "{n} installed",
        "chip_updates": "{n} updates",
        "btn_get": "GET",
        "btn_open": "OPEN",
        "btn_update": "UPDATE",
        "btn_remove": "Remove",
        "btn_back": "Back",
        "btn_copy": "Copy",
        "btn_copied": "Copied",
        "btn_update_all": "Update all ({n})",
        "btn_refresh": "Refresh",
        "pill_installed": "INSTALLED",
        "pill_update": "UPDATE",
        "pill_busy": "IN TERMINAL",
        "pill_local": "LOCAL BUILD",
        "lbl_version": "VERSION",
        "lbl_installed_ver": "INSTALLED",
        "lbl_download": "DOWNLOAD",
        "lbl_size": "INSTALLED SIZE",
        "lbl_license": "LICENSE",
        "lbl_built": "BUILT",
        "lbl_about": "ABOUT",
        "lbl_command": "COMMAND THAT WILL RUN",
        "lbl_command_remove": "REMOVE COMMAND",
        "lbl_depends": "DEPENDS ON",
        "lbl_optdepends": "OPTIONAL",
        "lbl_website": "Website",
        "cmd_note": "A terminal window opens and runs this. sudo asks for your "
                    "password every time; pacman shows what will change and waits "
                    "for your confirmation. -Syu also brings the rest of the system up "
                    "to date, because installing against a newer repo without it is a "
                    "partial upgrade.",
        "remove_note": "Removing runs: {cmd}",
        "empty_search": "Nothing matches “{q}”.",
        "empty_installed": "No Maze apps installed yet.",
        "empty_updates": "Everything is up to date.",
        "empty_repo": "The package list could not be loaded. "
                      "Check your connection and press Refresh.",
        "src_network": "Live catalogue",
        "src_cache": "Cached catalogue",
        "src_system": "System package database",
        "src_none": "No catalogue",
        "src_offline": "offline",
        "src_fetching": "Refreshing…",
        "status_line": "{src} · {n} apps · updated {age}",
        "age_now": "just now",
        "age_min": "{n} min ago",
        "age_hour": "{n} h ago",
        "age_day": "{n} d ago",
        "err_title": "Could not open a terminal",
        "err_body": "Maze Store runs installs in a terminal so you can see and "
                    "authorise them. {why}\n\nYou can run the command yourself:\n\n{cmd}",
        "core_title": "Remove a system component?",
        "core_body": "{name} is part of how Maze Linux is put together. Removing it "
                     "can change or break parts of the desktop.\n\nRemove anyway?",
        "open_fail": "This package has no app to open from the menu.",
        "now_terminal": "Waiting for the terminal…",
    },
    "tr": {
        "search": "Uygulama ara",
        "tip_minimize": "Küçült",
        "tip_maximize": "Büyüt / Geri al",
        "tip_close": "Kapat",
        "notify_title": "Güncelleme bildirimi",
        "notify_hint": "6 saatte bir kontrol eder",
        "nav_browse": "KEŞFET",
        "nav_library": "KİTAPLIK",
        "cat_all": "Keşfet",
        "cat_privacy": "Gizlilik",
        "cat_security": "Güvenlik",
        "cat_ai": "Yapay Zekâ",
        "cat_crypto": "Kripto",
        "cat_desktop": "Masaüstü",
        "cat_system": "Sistem",
        "cat_other": "Diğer",
        "lib_installed": "Yüklü",
        "lib_updates": "Güncellemeler",
        "hero_title": "Bütün Maze uygulamaları,\ntek yerde.",
        "hero_sub": "[mazelinux] deposundan imzalı paketler. Kurulum terminalde "
                    "çalışır, şifreni sudo sorar — mağazanın kendisi asla root "
                    "yetkisi almaz.",
        "sec_featured": "Öne çıkanlar",
        "sec_all": "Tüm uygulamalar",
        "sec_results": "Sonuçlar",
        "sec_featured_sub": "Maze ekibinin Maze Linux için yaptığı uygulamalar.",
        "sec_all_sub": "Depodaki diğer her şey.",
        "hero_eyebrow": "MAZE LINUX",
        "count_apps": "{n} uygulama",
        "chip_installed": "{n} yüklü",
        "chip_updates": "{n} güncelleme",
        "btn_get": "İNDİR",
        "btn_open": "AÇ",
        "btn_update": "GÜNCELLE",
        "btn_remove": "Kaldır",
        "btn_back": "Geri",
        "btn_copy": "Kopyala",
        "btn_copied": "Kopyalandı",
        "btn_update_all": "Tümünü güncelle ({n})",
        "btn_refresh": "Yenile",
        "pill_installed": "YÜKLÜ",
        "pill_update": "GÜNCELLEME",
        "pill_busy": "TERMİNALDE",
        "pill_local": "YEREL SÜRÜM",
        "lbl_version": "SÜRÜM",
        "lbl_installed_ver": "YÜKLÜ SÜRÜM",
        "lbl_download": "İNDİRME",
        "lbl_size": "KURULU BOYUT",
        "lbl_license": "LİSANS",
        "lbl_built": "DERLENME",
        "lbl_about": "HAKKINDA",
        "lbl_command": "ÇALIŞTIRILACAK KOMUT",
        "lbl_command_remove": "KALDIRMA KOMUTU",
        "lbl_depends": "BAĞIMLILIKLAR",
        "lbl_optdepends": "İSTEĞE BAĞLI",
        "lbl_website": "Web sitesi",
        "cmd_note": "Bir terminal penceresi açılır ve bu komutu çalıştırır. sudo her "
                    "seferinde şifreni sorar; pacman neyin değişeceğini gösterir ve "
                    "onayını bekler. -Syu sistemin geri kalanını da günceller, çünkü "
                    "daha yeni bir depoya karşı onsuz kurulum kısmi güncelleme olur.",
        "remove_note": "Kaldırma şu komutu çalıştırır: {cmd}",
        "empty_search": "“{q}” ile eşleşen bir şey yok.",
        "empty_installed": "Henüz yüklü Maze uygulaması yok.",
        "empty_updates": "Her şey güncel.",
        "empty_repo": "Paket listesi yüklenemedi. Bağlantını kontrol edip "
                      "Yenile'ye bas.",
        "src_network": "Canlı katalog",
        "src_cache": "Önbellekteki katalog",
        "src_system": "Sistem paket veritabanı",
        "src_none": "Katalog yok",
        "src_offline": "çevrimdışı",
        "src_fetching": "Yenileniyor…",
        "status_line": "{src} · {n} uygulama · {age} güncellendi",
        "age_now": "az önce",
        "age_min": "{n} dk önce",
        "age_hour": "{n} sa önce",
        "age_day": "{n} gün önce",
        "err_title": "Terminal açılamadı",
        "err_body": "Maze Store kurulumları görüp onaylayabilmen için terminalde "
                    "çalıştırır. {why}\n\nKomutu kendin çalıştırabilirsin:\n\n{cmd}",
        "core_title": "Bir sistem bileşeni kaldırılsın mı?",
        "core_body": "{name}, Maze Linux'un bir parçası. Kaldırmak masaüstünün "
                     "bazı bölümlerini değiştirebilir ya da bozabilir.\n\nYine de "
                     "kaldırılsın mı?",
        "open_fail": "Bu paketin menüden açılacak bir uygulaması yok.",
        "now_terminal": "Terminal bekleniyor…",
    },
}

_lang = "tr" if QLocale.system().name().lower().startswith("tr") else "en"


def set_language(lang: str) -> None:
    global _lang
    if lang in STRINGS:
        _lang = lang


def language() -> str:
    return _lang


def t(key: str, **kw) -> str:
    s = STRINGS.get(_lang, {}).get(key) or STRINGS["en"].get(key) or key
    return s.format(**kw) if kw else s
