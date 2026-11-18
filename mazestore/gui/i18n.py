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
        "cmd_note": "A terminal window opens and runs this. Only this package is "
                    "installed: pacman checks its signature, shows what will change and "
                    "waits for your confirmation, and sudo asks for your password every "
                    "time. The rest of the system is left as it is.",
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
        "nav_sources": "MORE SOURCES",
        "src_arch": "Arch repositories",
        "src_aur": "AUR",
        "search_arch": "Search the Arch repositories",
        "search_aur": "Search the AUR",
        "arch_eyebrow": "ARCH LINUX",
        "arch_title": "Arch repositories",
        "arch_sub": "Official packages from core, extra and multilib, signed by the "
                    "Arch Linux developers. Installs run pacman -S --needed in a "
                    "terminal: just that package, the rest of the system is left as it is.",
        "aur_eyebrow": "ARCH USER REPOSITORY",
        "aur_title": "AUR",
        "aur_sub": "Build scripts submitted by users and reviewed by no one. A terminal "
                   "opens, {helper} shows you the PKGBUILD, and you decide. Read it "
                   "before you accept.",
        "aur_no_helper": "paru is not installed. Maze Store builds AUR packages with paru.",
        "btn_get_paru": "Install paru",
        "ext_hint": "Type in the search box above to search.",
        "ext_short": "Type at least {n} characters to search the AUR.",
        "ext_searching": "Searching…",
        "ext_error": "The search failed: {why}",
        "ext_more": "Showing the first {shown} of {n}. Narrow the search to see the rest.",
        "count_pkgs": "{n} packages",
        "btn_remove_short": "REMOVE",
        "pill_ood": "OUT OF DATE",
        "pill_orphan": "ORPHAN",
        "meta_votes": "{n} votes",
        "tip_aur_page": "Open the AUR page: PKGBUILD, comments, history",
        "status_ext": "{src} · {n} results",
        "aur_confirm_title": "Install from the AUR?",
        "aur_confirm_body": "{name} is built from a script a user uploaded to the AUR. "
                            "Nobody has reviewed it.\n\nA terminal opens and {helper} "
                            "shows you the PKGBUILD first. Read it before you accept; "
                            "sudo asks for your password only for the final install."
                            "\n\nContinue?",
        "upd_maze_sub": "from the Maze repository",
        "upd_arch_sub": "from the Arch repositories",
        "upd_aur_sub": "built from the AUR",
        "upd_checking": "Checking for updates…",
        "upd_check_failed": "Could not check the Arch repositories (offline?). Press Refresh to try again.",
        "one_title": "Update just this package?",
        "one_body": "{name} depends on packages that have updates of their own:\n\n{list}\n\n"
                    "Only {name} will be updated, and the system's databases are not "
                    "refreshed. If the new {name} was built against the newer versions "
                    "above, it may not start until you update the whole system.",
        "one_only": "Just this package",
        "one_all": "Update whole system",
        "paru_title": "paru is not installed",
        "paru_body": "AUR packages are built with paru, which is in the Maze "
                     "repository. Install it now?",
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
        "cmd_note": "Bir terminal penceresi açılır ve bu komutu çalıştırır. Yalnızca bu "
                    "paket kurulur: pacman imzasını doğrular, neyin değişeceğini gösterir "
                    "ve onayını bekler; sudo her seferinde şifreni sorar. Sistemin geri "
                    "kalanına dokunulmaz.",
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
        "nav_sources": "DİĞER KAYNAKLAR",
        "src_arch": "Arch depoları",
        "src_aur": "AUR",
        "search_arch": "Arch depolarında ara",
        "search_aur": "AUR'da ara",
        "arch_eyebrow": "ARCH LINUX",
        "arch_title": "Arch depoları",
        "arch_sub": "core, extra ve multilib'den resmi paketler, Arch Linux "
                    "geliştiricileri tarafından imzalı. Kurulum terminalde "
                    "pacman -S --needed ile çalışır: yalnızca o paket, sistemin geri kalanına dokunulmaz.",
        "aur_eyebrow": "ARCH KULLANICI DEPOSU",
        "aur_title": "AUR",
        "aur_sub": "Kullanıcıların yüklediği ve kimsenin denetlemediği derleme "
                   "betikleri. Bir terminal açılır, {helper} sana PKGBUILD'i gösterir "
                   "ve kararı sen verirsin. Onaylamadan önce oku.",
        "aur_no_helper": "paru kurulu değil. Maze Store AUR paketlerini paru ile derler.",
        "btn_get_paru": "paru'yu kur",
        "ext_hint": "Aramak için yukarıdaki kutuya yaz.",
        "ext_short": "AUR'da aramak için en az {n} karakter yaz.",
        "ext_searching": "Aranıyor…",
        "ext_error": "Arama başarısız oldu: {why}",
        "ext_more": "{n} sonucun ilk {shown} tanesi gösteriliyor. Gerisi için aramayı daralt.",
        "count_pkgs": "{n} paket",
        "btn_remove_short": "KALDIR",
        "pill_ood": "GÜNCEL DEĞİL",
        "pill_orphan": "SAHİPSİZ",
        "meta_votes": "{n} oy",
        "tip_aur_page": "AUR sayfasını aç: PKGBUILD, yorumlar, geçmiş",
        "status_ext": "{src} · {n} sonuç",
        "aur_confirm_title": "AUR'dan kurulsun mu?",
        "aur_confirm_body": "{name}, bir kullanıcının AUR'a yüklediği bir betikle "
                            "derlenir. Kimse onu denetlemedi.\n\nBir terminal açılır ve "
                            "{helper} önce PKGBUILD'i gösterir. Onaylamadan önce oku; "
                            "sudo şifreni yalnızca son kurulum için sorar.\n\nDevam edilsin mi?",
        "upd_maze_sub": "Maze deposundan",
        "upd_arch_sub": "Arch depolarından",
        "upd_aur_sub": "AUR'dan derlenmiş",
        "upd_checking": "Güncellemeler kontrol ediliyor…",
        "upd_check_failed": "Arch depoları kontrol edilemedi (çevrimdışı mı?). Tekrar denemek için Yenile'ye bas.",
        "one_title": "Yalnızca bu paket güncellensin mi?",
        "one_body": "{name}, kendi güncellemesi bekleyen paketlere bağlı:\n\n{list}\n\n"
                    "Yalnızca {name} güncellenir; sistemin paket veritabanı yenilenmez. "
                    "Yeni {name} yukarıdakilerin yeni sürümleriyle derlendiyse, tüm sistemi "
                    "güncelleyene kadar açılmayabilir.",
        "one_only": "Yalnızca bu paket",
        "one_all": "Tüm sistemi güncelle",
        "paru_title": "paru kurulu değil",
        "paru_body": "AUR paketleri Maze deposunda bulunan paru ile derlenir. "
                     "Şimdi kurulsun mu?",
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
