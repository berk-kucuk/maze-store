"""Core tests. No network, no root, and no command is ever executed."""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mazestore.core import actions, catalog, dbparse, external, local, model  # noqa: E402


def make_db(descs: dict[str, str], compression: str = "gz") -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode=f"w:{compression}") as tar:
        for dirname, text in descs.items():
            d = tarfile.TarInfo(dirname)
            d.type = tarfile.DIRTYPE
            tar.addfile(d)
            data = text.encode()
            info = tarfile.TarInfo(f"{dirname}/desc")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


DESC = """%FILENAME%
maze-cloak-1.3.4-1-any.pkg.tar.zst

%NAME%
maze-cloak

%VERSION%
1.3.4-1

%DESC%
MAC randomisation

%CSIZE%
1000

%ISIZE%
2000

%LICENSE%
GPL3

%DEPENDS%
maze-python
iproute2

"""


class DbParse(unittest.TestCase):
    def test_parse_desc(self):
        f = dbparse.parse_desc(DESC)
        self.assertEqual(f["NAME"], ["maze-cloak"])
        self.assertEqual(f["DEPENDS"], ["maze-python", "iproute2"])

    def test_read_db(self):
        pkgs = dbparse.read_db(make_db({"maze-cloak-1.3.4-1": DESC}))
        p = pkgs["maze-cloak"]
        self.assertEqual((p.version, p.csize, p.isize), ("1.3.4-1", 1000, 2000))
        self.assertEqual(p.depends, ["maze-python", "iproute2"])

    def test_garbage_rejected(self):
        with self.assertRaises(ValueError):
            dbparse.read_db(b"<html>not a db</html>")

    def test_empty_db_rejected(self):
        with self.assertRaises(ValueError):
            dbparse.read_db(make_db({}))

    def test_desc_without_name_skipped(self):
        db = make_db({"a-1": "%VERSION%\n1\n", "maze-cloak-1.3.4-1": DESC})
        self.assertEqual(list(dbparse.read_db(db)), ["maze-cloak"])


class Vercmp(unittest.TestCase):
    CASES = [("1.0", "1.0a"), ("1.0a", "1.0"), ("1.0-1", "1.0-2"),
             ("0.5.1-1", "0.4.1-1"), ("1:1.0", "2.0"), ("1.0.0", "1.0"),
             ("1.0rc1", "1.0"), ("2.1.10-1", "2.1.9-1"), ("1..0", "1.0"),
             ("20240212-1", "20240212-1"), ("1.0", "1.0.a"), ("1.a", "1.0"),
             ("1.0-1", "1.0"), ("2.20.4-1", "2.20.4-2"), ("1.0.0-10", "1.0.0-9")]

    def test_against_pacman(self):
        try:
            subprocess.run(["vercmp", "1", "1"], capture_output=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("vercmp not available")
        for a, b in self.CASES:
            ref = int(subprocess.run(["vercmp", a, b], capture_output=True,
                                     text=True).stdout)
            self.assertEqual(local.vercmp(a, b), (ref > 0) - (ref < 0), (a, b))


class Actions(unittest.TestCase):
    def test_install_command(self):
        self.assertEqual(actions.pacman_argv("install", ["maze-cloak"]),
                         ["sudo", "-k", "pacman", "-Syu", "--needed", "--", "maze-cloak"])
        self.assertEqual(actions.display_command("install", ["maze-cloak"]),
                         "sudo pacman -Syu --needed maze-cloak")

    def test_remove_and_upgrade(self):
        self.assertEqual(actions.pacman_argv("remove", ["qlam"])[:4],
                         ["sudo", "-k", "pacman", "-Rns"])
        self.assertEqual(actions.pacman_argv("upgrade", []),
                         ["sudo", "-k", "pacman", "-Syu"])

    def test_always_asks_password(self):
        for act, pk in (("install", ["a"]), ("remove", ["a"]), ("upgrade", [])):
            argv = actions.pacman_argv(act, pk)
            self.assertEqual(argv[:2], ["sudo", "-k"])
            self.assertNotIn("--noconfirm", argv)

    def test_hostile_names_rejected(self):
        for bad in ["-Rdd", "--config=/tmp/x", "a b", "a;rm", "$(id)", "A", "", ".x",
                    "x" * 200, "a\nb"]:
            self.assertFalse(actions.valid_name(bad), bad)
            with self.assertRaises(ValueError):
                actions.pacman_argv("install", [bad])

    def test_unknown_action(self):
        with self.assertRaises(ValueError):
            actions.pacman_argv("sync", ["a"])

    def test_terminal_argv_keeps_names_separate(self):
        with mock.patch.object(actions, "find_terminal", return_value=("/usr/bin/konsole", ["-e"])), \
             mock.patch.object(actions, "runner", return_value=Path("/opt/maze-store/maze-store-run")):
            argv = actions.terminal_argv("install", ["maze-cloak", "qlam"])
        self.assertEqual(argv, ["/usr/bin/konsole", "-e", "/opt/maze-store/maze-store-run",
                                "install", "maze-cloak", "qlam"])

    def test_runner_script_rejects_bad_names(self):
        script = Path(__file__).resolve().parents[1] / "maze-store-run"
        # stdin is closed so the final "press a key" read returns at once;
        # validation fails before sudo is ever reached.
        r = subprocess.run(["bash", str(script), "install", "--root=/"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=10)
        self.assertEqual(r.returncode, 2)
        r = subprocess.run(["bash", str(script), "frobnicate", "x"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=10)
        self.assertEqual(r.returncode, 2)


class AurActions(unittest.TestCase):
    def test_aur_install_runs_helper_as_user(self):
        with mock.patch.object(actions, "aur_helper", return_value="paru"):
            argv = actions.pacman_argv("aur-install", ["yay-bin"])
            self.assertEqual(argv, ["paru", "-S", "--needed", "yay-bin"])
            self.assertEqual(actions.display_command("aur-install", ["yay-bin"]),
                             "paru -S --needed yay-bin")
        self.assertNotIn("sudo", argv)
        self.assertNotIn("--noconfirm", argv)

    def test_aur_hostile_names_rejected(self):
        for bad in ["-Rdd", "--sudo=/tmp/x", "a b", "$(id)", ""]:
            with self.assertRaises(ValueError):
                actions.pacman_argv("aur-install", [bad])

    def test_runner_rejects_bad_aur_names(self):
        script = Path(__file__).resolve().parents[1] / "maze-store-run"
        r = subprocess.run(["bash", str(script), "aur-install", "--sudo=/tmp/x"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=10)
        self.assertEqual(r.returncode, 2)


SS = """core/linux 6.12.1-1 (base) [installed]
    The Linux kernel and modules
extra/vim 9.1-1
    Vi Improved, a highly configurable,
    improved version of the vi text editor
mazelinux/maze-cloak 1.3.4-1
    MAC randomisation
weird line
extra/-bad 1-1
    should be skipped
"""


class External(unittest.TestCase):
    def test_parse_pacman_ss(self):
        pkgs = external.parse_pacman_ss(SS)
        self.assertEqual([(p.repo, p.name, p.version) for p in pkgs],
                         [("core", "linux", "6.12.1-1"), ("extra", "vim", "9.1-1")])
        self.assertEqual(pkgs[1].desc,
                         "Vi Improved, a highly configurable, improved version of the vi text editor")

    def test_search_argv_keeps_words_terms(self):
        self.assertEqual(external.pacman_search_argv(["-Rdd", "x"]),
                         ["pacman", "-Ss", "--", "-Rdd", "x"])

    def test_parse_aur(self):
        doc = {"resultcount": 4, "type": "search", "results": [
            {"Name": "yay-bin", "Version": "12.4-1", "Description": "AUR helper",
             "NumVotes": 500, "Popularity": 9.5, "Maintainer": "jguer", "OutOfDate": None},
            {"Name": "yay-git", "Version": "12-1", "Description": "AUR helper (git)",
             "NumVotes": 50, "Popularity": 1.0, "Maintainer": None, "OutOfDate": 1700000000},
            {"Name": "Bad Name", "Version": "1-1"},
            {"Name": "other", "Version": "1-1", "Description": "unrelated"},
        ]}
        import json
        pkgs = external.parse_aur(json.dumps(doc).encode(), ["yay", "helper"])
        self.assertEqual([p.name for p in pkgs], ["yay-bin", "yay-git"])
        self.assertTrue(pkgs[1].out_of_date)
        self.assertEqual(pkgs[1].maintainer, "")
        with self.assertRaises(ValueError):
            external.parse_aur(b'{"type":"error","error":"Too many package results."}', ["a"])
        with self.assertRaises(ValueError):
            external.parse_aur(b"<html>", ["a"])

    def test_aur_url_quotes_term(self):
        url = external.aur_search_url(["a/../b?x=1"])
        self.assertTrue(url.startswith("https://aur.archlinux.org/rpc/v5/search/a%2F..%2Fb%3Fx%3D1"))
        self.assertEqual(external.aur_term(["ab", "longer"]), "longer")

    def test_rank_and_state(self):
        pkgs = [external.ExtPackage(n, "1.0-1", "", "arch") for n in ("libvim", "vim-x", "vim")]
        self.assertEqual([p.name for p in external.rank(pkgs, ["vim"])],
                         ["vim", "vim-x", "libvim"])
        external.mark_installed(pkgs, {"vim": "0.9-1", "libvim": "1.0-1"})
        self.assertEqual({p.name: p.state for p in pkgs},
                         {"vim": "update", "libvim": "installed", "vim-x": "available"})


class SinglePackage(unittest.TestCase):
    URL = "https://mazerepo.berkkucukk.com.tr/packages/maze-terminal-1.1.1-3-x86_64.pkg.tar.zst"

    def test_install_file_is_just_that_file(self):
        argv = actions.pacman_argv("install-file", [self.URL])
        self.assertEqual(argv, ["sudo", "-k", "pacman", "-U", "--needed", "--", self.URL])
        self.assertNotIn("-Syu", argv)
        self.assertEqual(actions.pacman_argv("install-only", ["vim"]),
                         ["sudo", "-k", "pacman", "-S", "--needed", "--", "vim"])

    def test_bad_urls_rejected(self):
        for bad in ["http://x.org/a-1-1-any.pkg.tar.zst", "https://x.org/../a-1-1-any.pkg.tar.zst",
                    "https://x.org/a-1-1-any.pkg.tar.zst;id", "https://x.org/a.sh",
                    "file:///tmp/a-1-1-any.pkg.tar.zst", "https://x.org/a b-1-1-any.pkg.tar.zst",
                    "--config=/tmp/x"]:
            self.assertFalse(actions.valid_url(bad), bad)
            with self.assertRaises(ValueError):
                actions.pacman_argv("install-file", [bad])
        # A URL is not a package name, and a name is not a URL.
        with self.assertRaises(ValueError):
            actions.pacman_argv("install", [self.URL])

    def test_runner_rejects_bad_urls(self):
        script = Path(__file__).resolve().parents[1] / "maze-store-run"
        for bad in ["https://x.org/../a-1-1-any.pkg.tar.zst", "https://x.org/a-1-1.pkg.tar.zst;id",
                    "--root=/"]:
            r = subprocess.run(["bash", str(script), "install-file", bad],
                               capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=10)
            self.assertEqual(r.returncode, 2, bad)


class AurUpdates(unittest.TestCase):
    def test_foreign_and_info(self):
        foreign = external.parse_foreign("yay-bin 12.3-1\nobsidian-bin 1.14.4-1\nbad line here\n")
        self.assertEqual(foreign, {"yay-bin": "12.3-1", "obsidian-bin": "1.14.4-1"})
        urls = external.aur_info_urls(list(foreign))
        self.assertEqual(urls, [external.AUR_INFO + "?arg[]=obsidian-bin&arg[]=yay-bin"])
        self.assertEqual(len(external.aur_info_urls([f"p{i}" for i in range(250)])), 3)
        info = [external.ExtPackage("yay-bin", "12.4-1", "", "aur"),
                external.ExtPackage("obsidian-bin", "1.14.4-1", "", "aur")]
        self.assertEqual([p.name for p in external.aur_updates(info, foreign)], ["yay-bin"])


class SysCheck(unittest.TestCase):
    def test_dep_name_and_output(self):
        from mazestore.core import syscheck
        self.assertEqual(syscheck.dep_name("qt6-base>=6.8"), "qt6-base")
        self.assertEqual(syscheck.dep_name("libfoo.so=1-64"), "libfoo.so")
        self.assertEqual(syscheck.parse_output('{"pending": [{"name": "a"}, 3]}'), [{"name": "a"}])
        self.assertIsNone(syscheck.parse_output("garbage"))

    def test_parse_qu(self):
        from mazestore.core import syscheck
        out = "linux 6.12-1 -> 6.13-1\nbluedevil 1:6.8.2-1 -> 1:6.8.3-1 [ignored]\n:: noise\n"
        self.assertEqual(syscheck.parse_qu(out),
                         [("linux", "6.12-1", "6.13-1"), ("bluedevil", "1:6.8.2-1", "1:6.8.3-1")])


class Model(unittest.TestCase):
    def setUp(self):
        mk = lambda n, v: dbparse.RepoPackage(n, v, desc=f"{n} desc")
        self.pkgs = {p.name: p for p in [
            mk("maze-cloak", "1.3.4-1"), mk("qlam", "2.0.3-1"), mk("maze-crypto", "0.4.1-1"),
            mk("sentinai-debug", "1-1"), mk("mazelinux-keyring", "1-1"), mk("brand-new", "0.1-1")]}

    def test_states_and_hidden(self):
        apps = {a.name: a for a in model.build(self.pkgs, {
            "maze-cloak": "1.3.4-1", "qlam": "2.0.2-1", "maze-crypto": "0.5.1-1"})}
        self.assertNotIn("sentinai-debug", apps)
        self.assertNotIn("mazelinux-keyring", apps)
        self.assertEqual(apps["maze-cloak"].state, "installed")
        self.assertEqual(apps["qlam"].state, "update")
        self.assertEqual(apps["maze-crypto"].state, "local")
        self.assertEqual(apps["brand-new"].state, "available")
        self.assertEqual(apps["brand-new"].entry.category, "other")

    def test_select(self):
        apps = model.build(self.pkgs, {"qlam": "2.0.2-1"})
        self.assertEqual([a.name for a in model.select(apps, "updates")], ["qlam"])
        self.assertEqual([a.name for a in model.select(apps, "all", "mac adres")], ["maze-cloak"])
        self.assertTrue(all(a.entry.category == "privacy"
                            for a in model.select(apps, "privacy")))


class Catalog(unittest.TestCase):
    def test_entries_are_complete(self):
        for name, e in catalog.CATALOG.items():
            self.assertIn(e.category, catalog.CATEGORIES, name)
            self.assertTrue(e.tagline_en and e.tagline_tr, name)
            self.assertTrue(actions.valid_name(name), name)


class Desktop(unittest.TestCase):
    def test_exec_argv(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".desktop", delete=False) as f:
            f.write("[Desktop Entry]\nName=X\nExec=/usr/bin/maze-cloak --flag %U\n"
                    "[Desktop Action new]\nExec=/bin/false\n")
        self.assertEqual(local.exec_argv(Path(f.name)), ["/usr/bin/maze-cloak", "--flag"])
        Path(f.name).unlink()


class Checker(unittest.TestCase):
    """The background check: what it announces, and that it announces once."""

    def setUp(self):
        import tempfile
        from mazestore.core import checker
        self.checker = checker
        self.tmp = tempfile.TemporaryDirectory()
        env = {"XDG_STATE_HOME": self.tmp.name + "/state",
               "XDG_CONFIG_HOME": self.tmp.name + "/config",
               "XDG_CACHE_HOME": self.tmp.name + "/cache"}
        self.env = mock.patch.dict("os.environ", env)
        self.env.start()
        mk = lambda n, v: dbparse.RepoPackage(n, v)
        self.repo = {"qlam": mk("qlam", "2.0.3-1"), "maze-cloak": mk("maze-cloak", "1.3.4-1")}
        self.installed = {"qlam": "2.0.2-1", "maze-cloak": "1.3.4-1"}
        self.patches = [
            mock.patch.object(checker, "fetch", return_value=True),
            mock.patch.object(checker.repo, "load_local",
                              side_effect=lambda: checker.repo.Catalogue(self.repo, "cache", 1.0)),
            mock.patch.object(checker.local, "installed", side_effect=lambda: dict(self.installed)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_notifies_once_per_version(self):
        with mock.patch.object(self.checker, "notify") as n:
            self.checker.run([])
            self.checker.run([])
        self.assertEqual(n.call_count, 1)
        self.assertEqual([a.name for a in n.call_args[0][0]], ["qlam"])

    def test_new_version_is_announced_again(self):
        with mock.patch.object(self.checker, "notify") as n:
            self.checker.run([])
            self.repo["qlam"] = dbparse.RepoPackage("qlam", "2.0.4-1")
            self.checker.run([])
        self.assertEqual(n.call_count, 2)

    def test_no_notify_does_not_mark_seen(self):
        with mock.patch.object(self.checker, "notify") as n:
            self.checker.run(["--no-notify"])
            self.checker.run([])
        self.assertEqual(n.call_count, 1)

    def test_nothing_pending_no_notification(self):
        self.installed["qlam"] = "2.0.3-1"
        with mock.patch.object(self.checker, "notify") as n:
            self.checker.run([])
        n.assert_not_called()

    def test_switched_off_in_settings(self):
        from mazestore.core import settings
        settings.save({"notify_updates": False})
        with mock.patch.object(self.checker, "notify") as n:
            self.checker.run([])
        n.assert_not_called()
        self.checker.fetch.assert_not_called()

    def test_message_text(self):
        apps = model.build(self.repo, {"qlam": "1-1", "maze-cloak": "1-1"})
        title, body, _ = self.checker.message(apps, "tr")
        self.assertIn("2 Maze güncellemesi", title)
        self.assertIn("Qlam", body)


class I18n(unittest.TestCase):
    def test_tables_match(self):
        from mazestore.gui.i18n import STRINGS
        self.assertEqual(set(STRINGS["en"]), set(STRINGS["tr"]))


if __name__ == "__main__":
    unittest.main()


class SignedDbTests(unittest.TestCase):
    """ST1: the store only caches — and only reads back — a db signed by the
    Maze key. ST2: a db that unpacks to far more than it could hold is refused
    before it is decompressed."""

    SYNC = Path("/var/lib/pacman/sync/mazelinux.db")

    def setUp(self):
        import tempfile as _t
        self.tmp = Path(_t.mkdtemp(prefix="maze-store-test-"))
        self._old = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil as _sh
        if self._old is None:
            os.environ.pop("XDG_CACHE_HOME", None)
        else:
            os.environ["XDG_CACHE_HOME"] = self._old
        _sh.rmtree(self.tmp, ignore_errors=True)

    def _real(self):
        from mazestore.core import repo
        sig = self.SYNC.with_name(self.SYNC.name + ".sig")
        if not (self.SYNC.is_file() and sig.is_file() and repo.KEYRING.is_file()):
            self.skipTest("no signed Maze db on this machine")
        return self.SYNC.read_bytes(), sig.read_bytes()

    def test_real_signed_db_verifies_and_is_cached(self):
        from mazestore.core import repo
        data, sig = self._real()
        self.assertTrue(repo.verify(data, sig))
        repo.save_cache(data, sig)
        self.assertEqual(repo.load_local().source in ("cache", "system"), True)
        self.assertTrue(repo.cache_db().exists())

    def test_tampered_or_unsigned_db_is_refused(self):
        from mazestore.core import repo
        data, sig = self._real()
        self.assertFalse(repo.verify(data + b"\0", sig))
        self.assertFalse(repo.verify(data, b""))
        with self.assertRaises(ValueError):
            repo.save_cache(data, b"not a signature")
        self.assertFalse(repo.cache_db().exists())

    def test_cache_without_signature_is_not_read(self):
        from mazestore.core import repo
        data, _sig = self._real()
        repo.cache_dir().mkdir(parents=True, exist_ok=True)
        repo.cache_db().write_bytes(data)           # planted, no .sig
        self.assertIsNone(repo._load(repo.cache_db(), require_sig=True))

    def test_decompression_bomb_is_refused_quickly(self):
        import io as _io
        import tarfile as _tar
        import time as _time
        from mazestore.core import dbparse
        buf = _io.BytesIO()
        with _tar.open(fileobj=buf, mode="w:gz", compresslevel=1) as t:
            info = _tar.TarInfo("filler")
            info.size = dbparse.MAX_UNPACKED_BYTES + 1

            class Zeros:
                left = info.size

                def read(self, n=-1):
                    n = self.left if n < 0 else min(n, self.left)
                    self.left -= n
                    return b"\0" * n
            t.addfile(info, Zeros())
            desc = b"%NAME%\nx\n\n%VERSION%\n1-1\n"
            d = _tar.TarInfo("x-1-1/desc")
            d.size = len(desc)
            t.addfile(d, _io.BytesIO(desc))
        data = buf.getvalue()
        self.assertLess(len(data), dbparse.MAX_DB_BYTES)
        start = _time.monotonic()
        with self.assertRaises(ValueError):
            dbparse.read_db(data)
        self.assertLess(_time.monotonic() - start, 1.0, "the bomb was decompressed")

    def test_notified_state_uses_a_fresh_temp_name(self):
        """ST3."""
        src = (Path(__file__).resolve().parents[1] / "mazestore/core/checker.py").read_text()
        self.assertNotIn('with_suffix(".tmp")', src)
        self.assertIn("mkstemp", src)
