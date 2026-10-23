"""Packaging, translations and example validation."""

import ast
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components/nettleievakt"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def leaves(value, prefix=""):
    if not isinstance(value, dict):
        return {prefix}
    return set().union(*(leaves(item, f"{prefix}.{key}") for key, item in value.items()))


def test_translations_match_and_cover_every_entity():
    strings = read_json(COMPONENT / "strings.json")
    assert read_json(COMPONENT / "translations/en.json") == strings
    assert leaves(read_json(COMPONENT / "translations/nb.json")) == leaves(strings)
    assert len(strings["entity"]["sensor"]) == 6
    assert "hourly_target_risk" in strings["entity"]["binary_sensor"]
    assert "target_kw" in strings["entity"]["number"]


def test_manifest_has_no_vendor_dependencies():
    manifest = read_json(COMPONENT / "manifest.json")
    assert manifest["domain"] == "nettleievakt"
    assert manifest["config_flow"]
    assert manifest["iot_class"] == "calculated"
    assert manifest["requirements"] == []
    assert manifest["codeowners"] == ["@ThomasStaal"]
    assert read_json(ROOT / "hacs.json")["homeassistant"] == "2026.10.0"
    assert manifest["dependencies"] == ["panel_custom"]


def test_frontend_packaged_and_versioned():
    manifest = read_json(COMPONENT / "manifest.json")
    code = (COMPONENT / "www/panel.js").read_text(encoding="utf-8")
    assert f"dashboard-model.mjs?v={manifest['version']}" in code
    assert (COMPONENT / "www/dashboard-model.mjs").is_file()
    assert "nettleievakt-panel" in code
    assert 'callService("number", "set_value"' in code
    assert "fetch(" not in code
    assert "https://" not in code


def test_component_has_no_network_client_or_service_calls():
    forbidden = {"requests", "httpx", "aiohttp", "socket", "urllib", "paho"}
    for path in COMPONENT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] not in forbidden for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden
        assert "hass.services.async_call" not in path.read_text(encoding="utf-8")


def test_example_yaml_and_blueprint():
    dashboard = yaml.safe_load((ROOT / "examples/dashboard.yaml").read_text(encoding="utf-8"))
    assert len(dashboard["cards"]) == 3

    class BlueprintLoader(yaml.SafeLoader):
        pass

    BlueprintLoader.add_constructor("!input", lambda loader, node: loader.construct_scalar(node))
    blueprint = yaml.load(
        (ROOT / "blueprints/hourly-warning.yaml").read_text(encoding="utf-8"),
        Loader=BlueprintLoader,
    )
    assert blueprint["blueprint"]["domain"] == "automation"
    assert blueprint["triggers"][0]["for"]["minutes"] == 2
    assert blueprint["actions"] in blueprint["blueprint"]["input"]


def test_private_runtime_files_ignored():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in [".venv/", ".venv-ha/", ".storage/", "secrets.yaml", ".env*"]:
        assert entry in ignored
