import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_manifest_fields():
    text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
    assert "name: hermes-pocket" in text
    assert "version:" in text
    assert "description:" in text
    assert "author:" in text


def test_register_entrypoint_exists():
    spec = importlib.util.spec_from_file_location("hermes_pocket_entry", ROOT / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(getattr(mod, "register", None))
