import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import babel_fish
from babel_fish import (
    AnthropicMessages,
    BabelError,
    BackendError,
    Cache,
    FixtureBackend,
    Glossary,
    OpenAICompatible,
    Profile,
    translate,
)
from babel_fish import prompt as prompts
from babel_fish.cli import main

ROOT = Path(__file__).resolve().parent.parent
EM = chr(0x2014)
SRC = "Our product reduces costs by 20%."
GOOD = "Unser Produkt senkt die Kosten um 20 %."
BAD = "Unser Produkt senkt die Kosten um 25 %."
DE = Profile("de", "formal", "investor")


class TestPipeline(unittest.TestCase):
    def test_a_good_reply_is_accepted_at_once(self):
        b = FixtureBackend({SRC: GOOD})
        r = translate(SRC, DE, b)
        self.assertEqual((r.ok, r.text, len(r.attempts), r.chosen), (True, GOOD, 1, 0))

    def test_a_bad_reply_is_repaired_with_the_problems_spelled_out(self):
        calls = []

        def reply(system, user):
            calls.append(user)
            return BAD if len(calls) == 1 else GOOD

        r = translate(SRC, DE, FixtureBackend(reply))
        self.assertEqual((r.ok, r.text, len(r.attempts), r.chosen), (True, GOOD, 2, 1))
        self.assertIn("20", calls[1])
        self.assertIn(BAD, calls[1])
        self.assertIn("numbers in the source", calls[1])

    def test_gives_up_after_max_attempts_and_says_so(self):
        r = translate(SRC, DE, FixtureBackend(lambda s, u: BAD), max_attempts=2)
        self.assertEqual((r.ok, len(r.attempts)), (False, 2))
        self.assertEqual(r.violations[0].code, "number_missing")

    def test_the_best_attempt_wins_not_the_last(self):
        replies = iter([GOOD.replace("20", "21"), "Here is the translation: " + GOOD.replace("20", "21"), BAD])
        # attempt 1: one error; attempt 2: two errors; attempt 3: one error -> the later of the best two
        r = translate(SRC, DE, FixtureBackend(lambda s, u: next(replies)), max_attempts=3)
        self.assertEqual(r.chosen, 2)

    def test_protected_text_goes_back_in(self):
        src = "Hello {name}, see https://example.com/x for details."
        b = FixtureBackend(lambda s, u: "Hallo ⟦1⟧, siehe ⟦2⟧ für Details." if "⟦1⟧" in u else "")
        r = translate(src, Profile("de", "formal"), b)
        self.assertTrue(r.ok, r.violations)
        self.assertEqual(r.text, "Hallo {name}, siehe https://example.com/x für Details.")
        self.assertIn("⟦1⟧", b.calls[0][1])              # the backend never sees the placeholder itself
        self.assertNotIn("{name}", b.calls[0][1])

    def test_a_lost_placeholder_is_an_error(self):
        r = translate("Hello {name}, welcome to the new system we built.", Profile("de", "formal"), FixtureBackend(lambda s, u: "Hallo, willkommen im neuen System."), max_attempts=1)
        self.assertFalse(r.ok)
        self.assertEqual(r.violations[0].code, "placeholder")

    def test_glossary_reaches_the_prompt_and_the_check(self):
        g = Glossary.from_dict({"terms": {"data": "Daten"}, "keep": ["Acme Cloud"]})
        b = FixtureBackend(lambda s, u: "Acme Cloud schützt Ihre Informationen.")
        r = translate("Acme Cloud protects your data.", Profile("de", "formal"), b, glossary=g, max_attempts=1)
        self.assertEqual([v.code for v in r.violations], ["glossary"])
        self.assertIn('"data" must be "Daten"', b.calls[0][0])
        self.assertIn('"Acme Cloud"', b.calls[0][0])

    def test_cache_makes_the_second_run_free_and_identical(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "cache.jsonl")
            b1 = FixtureBackend({SRC: GOOD})
            r1 = translate(SRC, DE, b1, cache=Cache(path))
            b2 = FixtureBackend({})
            r2 = translate(SRC, DE, b2, cache=Cache(path))
            self.assertEqual((b2.calls, r2.text, r2.attempts[0].cached), ([], r1.text, True))
            self.assertEqual(r1.attempts[0].request_sha256, r2.attempts[0].request_sha256)

    def test_cache_key_changes_with_the_profile_and_the_backend(self):
        keys = {translate(SRC, p, FixtureBackend({SRC: GOOD}), max_attempts=1).attempts[0].request_sha256
                for p in (Profile("de", "formal", "investor"), Profile("de", "casual", "investor"), Profile("de", "formal", "legal"), Profile("fr", "formal", "investor"))}
        self.assertEqual(len(keys), 4)

    def test_a_damaged_cache_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.jsonl"
            p.write_text("not json\n", encoding="utf-8")
            with self.assertRaises(BabelError):
                Cache(str(p))

    def test_bad_arguments(self):
        with self.assertRaises(BabelError):
            translate("   ", DE, FixtureBackend({}))
        with self.assertRaises(BabelError):
            translate(SRC, DE, FixtureBackend({}), max_attempts=0)
        for args in (("xx",), ("de", "rude"), ("de", "formal", "poetry")):
            with self.assertRaises(BabelError):
                Profile(*args)

    def test_prompts_are_deterministic_and_describe_the_profile(self):
        a = prompts.system_prompt(Profile("de", "formal", "legal"))
        self.assertEqual(a, prompts.system_prompt(Profile("de", "formal", "legal")))
        self.assertIn('"Sie"', a)
        self.assertIn("1.234,56", a)
        self.assertIn('"du"', prompts.system_prompt(Profile("de", "casual")))
        self.assertIn("legal terminology", a)
        self.assertNotIn(EM, a)


class Fake(BaseHTTPRequestHandler):
    script: list = []
    seen: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.seen.append({"path": self.path, "headers": dict(self.headers), "body": body})
        status, payload, extra = Fake.script.pop(0)
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        for k, v in extra.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


class TestHttpBackends(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Fake)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Fake.script, Fake.seen = [], []
        self.sleeps = []

    def openai(self, **kw):
        return OpenAICompatible("m1", self.url + "/v1", api_key="sk-secret", sleep=self.sleeps.append, **kw)

    def test_openai_request_and_reply(self):
        Fake.script = [(200, {"choices": [{"message": {"content": "  Hallo  "}}]}, {})]
        self.assertEqual(self.openai().complete("SYS", "USER"), "Hallo")
        s = Fake.seen[0]
        self.assertEqual(s["path"], "/v1/chat/completions")
        self.assertEqual(s["headers"]["Authorization"], "Bearer sk-secret")
        self.assertEqual(s["body"], {"model": "m1", "temperature": 0, "messages": [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]})

    def test_anthropic_request_and_reply(self):
        Fake.script = [(200, {"content": [{"type": "text", "text": "Hallo "}, {"type": "text", "text": "Welt"}]}, {})]
        b = AnthropicMessages("claude-x", self.url, api_key="ak-secret", sleep=self.sleeps.append)
        self.assertEqual(b.complete("SYS", "USER"), "Hallo Welt")
        s = Fake.seen[0]
        h = {k.lower(): v for k, v in s["headers"].items()}
        self.assertEqual(s["path"], "/v1/messages")
        self.assertEqual((h["x-api-key"], h["anthropic-version"]), ("ak-secret", "2023-06-01"))
        self.assertEqual((s["body"]["system"], s["body"]["messages"], s["body"]["model"]), ("SYS", [{"role": "user", "content": "USER"}], "claude-x"))

    def test_rate_limit_is_retried_as_the_server_asks_then_succeeds(self):
        Fake.script = [(429, {"error": "slow down"}, {"Retry-After": "3"}), (503, {"error": "busy"}, {}),
                       (200, {"choices": [{"message": {"content": "ok"}}]}, {})]
        self.assertEqual(self.openai().complete("s", "u"), "ok")
        self.assertEqual(self.sleeps, [3.0, 2.0])

    def test_retry_wait_is_capped(self):
        Fake.script = [(429, {}, {"Retry-After": "9999"}), (200, {"choices": [{"message": {"content": "ok"}}]}, {})]
        self.openai().complete("s", "u")
        self.assertEqual(self.sleeps, [20.0])

    def test_a_client_error_is_not_retried_and_never_leaks_the_key(self):
        Fake.script = [(401, {"error": {"message": "bad key"}}, {})]
        with self.assertRaises(BackendError) as cm:
            self.openai().complete("s", "u")
        self.assertIn("401", str(cm.exception))
        self.assertNotIn("sk-secret", str(cm.exception))
        self.assertEqual((len(Fake.seen), self.sleeps), (1, []))

    def test_gives_up_after_the_retries(self):
        Fake.script = [(500, {}, {})] * 4
        with self.assertRaises(BackendError):
            self.openai(retries=3).complete("s", "u")
        self.assertEqual(len(Fake.seen), 4)

    def test_malformed_replies(self):
        for payload in (b"<html>", {"choices": []}, {"nope": 1}, [1, 2]):
            Fake.script = [(200, payload, {})]
            with self.assertRaises(BackendError):
                self.openai().complete("s", "u")

    def test_unreachable_server(self):
        b = OpenAICompatible("m", "http://127.0.0.1:9/v1", api_key="k", retries=1, sleep=self.sleeps.append, timeout=2)
        with self.assertRaises(BackendError) as cm:
            b.complete("s", "u")
        self.assertNotIn("k\n", str(cm.exception))

    def test_end_to_end_through_the_pipeline(self):
        Fake.script = [(200, {"choices": [{"message": {"content": BAD}}]}, {}), (200, {"choices": [{"message": {"content": GOOD}}]}, {})]
        r = translate(SRC, DE, self.openai())
        self.assertEqual((r.ok, r.text, len(Fake.seen)), (True, GOOD, 2))
        self.assertIn("numbers in the source", Fake.seen[1]["body"]["messages"][1]["content"])

    def test_cli_with_a_local_server(self):
        Fake.script = [(200, {"choices": [{"message": {"content": GOOD}}]}, {})]
        env = dict(os.environ, OPENAI_API_KEY="sk-test")
        r = subprocess.run([sys.executable, "-m", "babel_fish", "--input", SRC, "--lang", "de", "--tone", "formal", "--context", "investor", "--base-url", self.url + "/v1"],
                           capture_output=True, env=env, cwd=ROOT, timeout=60)
        self.assertEqual((r.returncode, r.stdout.decode("utf-8").strip()), (0, GOOD), r.stderr)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as e:
            code = int(e.code or 0)
    return code, out.getvalue(), err.getvalue()


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def write(self, name, text):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_verify_offline(self):
        s, good, bad = self.write("s.txt", SRC), self.write("g.txt", GOOD), self.write("b.txt", BAD)
        self.assertEqual(run("verify", "--source", s, "--output", good, "--to", "de")[0:2], (0, "no problems found\n"))
        code, out, _ = run("verify", "--source", s, "--output", bad, "--to", "de", "--json")
        self.assertEqual((code, json.loads(out)[0]["code"]), (1, "number_missing"))

    def test_prompt_offline(self):
        code, out, _ = run("prompt", "--to", "fr", "--tone", "casual", "--context", "marketing")
        self.assertEqual(code, 0)
        self.assertIn('"tu"', out)
        self.assertIn("marketing copy", out)

    def test_exit_2_without_a_backend_or_with_bad_input(self):
        env = {k: v for k, v in os.environ.items() if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")}
        r = subprocess.run([sys.executable, "-m", "babel_fish", "translate", "--text", "hi", "--to", "de"], capture_output=True, env=env, cwd=ROOT, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"no backend", r.stderr)
        self.assertEqual(run("verify", "--source", str(self.dir / "none"), "--output", str(self.dir / "none"), "--to", "de")[0], 2)
        self.assertEqual(run("translate", "--to", "de")[0], 2)
        self.assertEqual(run("verify", "--source", self.write("a", "x"), "--output", self.write("b", "y"), "--to", "xx")[0], 2)

    def test_no_em_dash_in_any_output(self):
        for args in (["--help"], ["prompt", "--to", "de"], ["prompt", "--to", "es", "--tone", "casual", "--context", "legal"]):
            self.assertNotIn(EM, run(*args)[1])

    def test_legacy_function(self):
        import babel_fish.backends as backends
        original = backends.from_environment
        backends.from_environment = lambda *a, **k: FixtureBackend({"Contracts bind.": "Verträge binden."})
        try:
            self.assertEqual(babel_fish.babel_fish("Contracts bind.", "de", "law"), "Verträge binden.")
        finally:
            backends.from_environment = original

    def test_no_em_dash_anywhere_in_the_repository(self):
        kinds = {".py", ".md", ".txt", ".toml", ".yml", ".json"}
        files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in kinds and ".git" not in p.parts and "__pycache__" not in p.parts]
        self.assertEqual([str(p.relative_to(ROOT)) for p in files if EM in p.read_text(encoding="utf-8")], [])


if __name__ == "__main__":
    unittest.main()
