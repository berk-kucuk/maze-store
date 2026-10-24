"""Core tests. No network, no root, and no command is ever executed."""
from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mazestore.core import actions, catalog, dbparse, local, model  # noqa: E402


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
