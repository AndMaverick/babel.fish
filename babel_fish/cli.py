"""babel-fish: translate, verify and show prompts.

    babel-fish translate --text "Our product reduces costs by 20%." --to de --tone formal
    babel-fish verify --source in.txt --output out.txt --to de --tone formal      (offline)
    babel-fish prompt --to fr --tone casual                                         (offline)

Exit codes: 0 translated and verified, 1 the best reply still has errors, 2 the input, a file or a backend could not be used."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import prompt as prompts
from . import protect, verify
from ._version import __version__
from .backends import from_environment
from .errors import BabelError
from .glossary import Glossary
from .langid import identify
from .pipeline import Cache, translate
from .profiles import CONTEXTS, LANGUAGES, TONES, Profile
from .violations import errors


def read_text(args: argparse.Namespace) -> str:
    sources = [x for x in (args.text, args.file) if x is not None]
    if len(sources) != 1:
        raise BabelError("give exactly one of --text or --file (use --file - for standard input)")
    if args.text is not None:
        return str(args.text)
    try:
        raw = sys.stdin.buffer.read() if args.file == "-" else Path(args.file).read_bytes()
        return raw.decode("utf-8-sig")
    except OSError as e:
        raise BabelError(f"cannot read {args.file}: {e.strerror or e}") from None
    except UnicodeDecodeError as e:
        raise BabelError(f"{args.file} is not valid UTF-8 (byte {e.start})") from None


def common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--to", "--lang", dest="to", required=True, choices=list(LANGUAGES), help="target language")
    p.add_argument("--tone", choices=list(TONES), default="formal")
    p.add_argument("--context", choices=list(CONTEXTS), default="general")
    p.add_argument("--glossary", help='JSON file: {"terms": {"source": "target"}, "keep": ["Name"]}')


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="babel-fish", description="Cultural calibration for translation: tone, context, and a verifier that checks the result.")
    p.add_argument("--version", action="version", version=f"babel.fish {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("translate", help="translate and verify")
    common(t)
    t.add_argument("--text", "--input", dest="text")
    t.add_argument("--file")
    t.add_argument("--from", dest="source")
    t.add_argument("--backend", choices=["openai", "anthropic"])
    t.add_argument("--model")
    t.add_argument("--base-url")
    t.add_argument("--attempts", type=int, default=3)
    t.add_argument("--cache", help="JSON lines file; repeated requests are answered from it")
    t.add_argument("--json", action="store_true")
    v = sub.add_parser("verify", help="check an existing translation, offline")
    common(v)
    v.add_argument("--source", required=True)
    v.add_argument("--output", required=True)
    v.add_argument("--from", dest="source_lang")
    v.add_argument("--json", action="store_true")
    pr = sub.add_parser("prompt", help="print the system prompt, offline")
    common(pr)
    pr.add_argument("--text", "--input", dest="text")
    pr.add_argument("--file")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0].startswith("--") and argv[0] not in ("--version", "-h", "--help"):
        argv = ["translate", *argv]                 # the original command line had no subcommand
    args = build_parser().parse_args(argv)
    try:
        profile = Profile(args.to, args.tone, args.context)
        glossary = Glossary.load(args.glossary) if args.glossary else None
        if args.cmd == "prompt":
            spans = len(protect.mask(read_text(args)).spans) if (args.text or args.file) else 0
            print(prompts.system_prompt(profile, glossary, spans))
            return 0
        if args.cmd == "verify":
            src = Path(args.source).read_text(encoding="utf-8-sig")
            out = Path(args.output).read_text(encoding="utf-8-sig")
            ms, mo = protect.mask(src), protect.mask(out)
            slang = args.source_lang or identify(src)
            problems = verify.check(ms.text, mo.text, source_lang="en" if slang == "unknown" else slang, target_lang=profile.language,
                                    tone=profile.tone, context=profile.context, spans=len(ms.spans), glossary=glossary)
            if args.json:
                print(json.dumps([x.to_dict() for x in problems], ensure_ascii=False, indent=1))
            else:
                for x in problems:
                    print(f"{x.severity}: {x.code}: {x.message}")
                if not problems:
                    print("no problems found")
            return 1 if errors(problems) else 0
        text = read_text(args)
        backend = from_environment(args.backend, args.model, args.base_url)
        result = translate(text, profile, backend, glossary=glossary, source_language=args.source, max_attempts=args.attempts, cache=Cache(args.cache))
    except (BabelError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=1, sort_keys=True))
    else:
        print(result.text)
        for v in result.violations:
            print(f"{v.severity}: {v.code}: {v.message}", file=sys.stderr)
    return 0 if result.ok else 1
