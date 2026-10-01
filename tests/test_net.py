from pocket import net


def test_custom_wins():
    cands = net.detect_candidates(9119, custom="https://x.example")
    assert len(cands) == 1
    assert cands[0].url == "https://x.example"
    assert cands[0].kind == "custom"


def test_lan_and_tailscale_listed(monkeypatch):
    monkeypatch.setattr(net, "all_lan_ips", lambda: ["192.168.1.3"])
    monkeypatch.setattr(net, "tailscale_ip", lambda: "100.64.0.9")
    urls = [c.url for c in net.detect_candidates(9119)]
    assert "http://192.168.1.3:9119" in urls
    assert "http://100.64.0.9:9119" in urls


def test_no_tailscale(monkeypatch):
    monkeypatch.setattr(net, "all_lan_ips", lambda: ["10.0.0.5"])
    monkeypatch.setattr(net, "tailscale_ip", lambda: None)
    cands = net.detect_candidates(9119)
    assert [c.kind for c in cands] == ["lan"]
