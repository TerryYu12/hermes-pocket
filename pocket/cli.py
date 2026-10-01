"""``hermes pocket ...`` CLI subcommands."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import net, qr


def register(ctx) -> None:
    ctx.register_cli_command(
        name="pocket",
        help="Hermes Pocket: pairing QR + remote-access checks for your phone",
        setup_fn=setup,
        handler_fn=handle,
    )


def setup(parser: argparse.ArgumentParser) -> None:
    subs = parser.add_subparsers(dest="pocket_command", required=False)
    p_qr = subs.add_parser("qr", help="Print a pairing QR (terminal) and optionally save a PNG")
    p_qr.add_argument("--url", default=None, help="Override the URL to encode (e.g. https://hermes.example.com)")
    p_qr.add_argument("--port", type=int, default=9119, help="Dashboard port to embed (default 9119)")
    p_qr.add_argument("--png", default=None, help="Also save a PNG to this path")
    p_qr.add_argument("--select", type=int, default=0, help="Which candidate to render (index, default 0)")
    p_qr.add_argument("--invert", action="store_true", help="Invert colors (for dark terminals)")
    p_qr.add_argument("--list", action="store_true", dest="list_only", help="Only list candidate URLs")
    p_qr.set_defaults(pocket_handler=_handle_qr)
    p_doc = subs.add_parser("doctor", help="Check remote-access prerequisites and print fixes")
    p_doc.set_defaults(pocket_handler=_handle_doctor)


def handle(args: argparse.Namespace) -> int:
    handler = getattr(args, "pocket_handler", None)
    if handler is None:
        print("usage: hermes pocket {qr} ...", file=sys.stderr)
        return 2
    return handler(args)


def _handle_qr(args: argparse.Namespace) -> int:
    cands = net.detect_candidates(args.port, custom=args.url)
    if not cands:
        print("No reachable address candidate found. Use --url to specify one.", file=sys.stderr)
        return 1
    for index, cand in enumerate(cands):
        print(f"[{index}] {cand.url}  ({cand.kind})")
    if args.list_only:
        return 0
    if not 0 <= args.select < len(cands):
        print(f"--select {args.select} out of range (0..{len(cands) - 1})", file=sys.stderr)
        return 2
    target = cands[args.select].url
    print()
    print(qr.render_ascii(qr.make_matrix(target), invert=args.invert))
    print(f"\n-> {target}")
    if args.png:
        out = Path(args.png).expanduser()
        out.write_bytes(qr.render_png(qr.make_matrix(target), invert=args.invert))
        print(f"PNG saved: {out}")
    return 0


_SYM = {"ok": "\u2713", "warn": "!", "fail": "\u2717", "info": "i"}


def _handle_doctor(args: argparse.Namespace) -> int:
    from . import probe

    checks = probe.run_all()
    for check in checks:
        print(f"[{_SYM.get(check.status, '?')}] {check.name}: {check.detail}")
        if check.fix and check.status in ("warn", "fail"):
            print(f"    -> {check.fix}")
    return 0 if all(c.status != "fail" for c in checks) else 1
