import argparse

from pocket import cli


def _ns(**over):
    ns = argparse.Namespace(
        port=9119, url=None, png=None, select=0, invert=False, list_only=False
    )
    for key, value in over.items():
        setattr(ns, key, value)
    return ns


def test_qr_lists_and_renders(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.net,
        "detect_candidates",
        lambda port, scheme="http", custom=None: [
            cli.net.Candidate("http://192.168.1.3:9119", "lan", "LAN")
        ],
    )
    assert cli._handle_qr(_ns()) == 0
    out = capsys.readouterr().out
    assert "http://192.168.1.3:9119" in out
    assert "\u2588" in out


def test_qr_custom_and_png(tmp_path):
    out_png = tmp_path / "qr.png"
    code = cli._handle_qr(_ns(url="https://x.example", png=str(out_png)))
    assert code == 0
    assert out_png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_qr_list_only(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.net,
        "detect_candidates",
        lambda port, scheme="http", custom=None: [
            cli.net.Candidate("http://a:9119", "lan", "LAN")
        ],
    )
    assert cli._handle_qr(_ns(list_only=True)) == 0
    out = capsys.readouterr().out
    assert "http://a:9119" in out
