import pathlib

import pytest
import yaml

_COMPOSE_PATH = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"


def _load_compose():
    if not _COMPOSE_PATH.exists():
        pytest.skip("docker-compose.yml not found (running inside container?)")
    with open(_COMPOSE_PATH) as f:
        return yaml.safe_load(f)


def test_no_hardcoded_passwords():
    compose = _load_compose()
    services = compose.get("services", {})
    for name, svc in services.items():
        env = svc.get("environment", [])
        if isinstance(env, list):
            for item in env:
                key_val = str(item)
                if "PASSWORD" in key_val.upper() or "SECRET" in key_val.upper():
                    assert (
                        "${" in key_val
                        or "_FILE" in key_val.upper()
                        or "/run/secrets" in key_val
                    ), f"Service '{name}' may have a hardcoded secret in: {key_val}"
        elif isinstance(env, dict):
            for k, v in env.items():
                if "PASSWORD" in k.upper() or "SECRET" in k.upper():
                    v_str = str(v)
                    assert (
                        "${" in v_str
                        or "_FILE" in k.upper()
                        or "/run/secrets" in v_str
                    ), f"Service '{name}' may have a hardcoded secret: {k}={v}"


def test_workers_have_healthcheck():
    compose = _load_compose()
    services = compose.get("services", {})
    for worker in ("webhook-worker", "arq-worker"):
        svc = services.get(worker)
        assert svc is not None, f"Service '{worker}' not found"
        assert "healthcheck" in svc, f"Service '{worker}' missing healthcheck"


def test_resource_limits_exist():
    compose = _load_compose()
    app_svc = compose["services"]["app"]
    assert "deploy" in app_svc
    assert "resources" in app_svc["deploy"]


def test_no_duplicate_env_vars():
    compose = _load_compose()
    services = compose.get("services", {})
    for name, svc in services.items():
        env = svc.get("environment", [])
        if isinstance(env, list):
            keys = []
            for item in env:
                key = str(item).split("=")[0].strip("- ")
                keys.append(key)
            assert len(keys) == len(set(keys)), f"Duplicate env vars in service '{name}': {keys}"


def test_logging_configured():
    compose = _load_compose()
    services = compose.get("services", {})
    for name, svc in services.items():
        assert "logging" in svc, f"Service '{name}' missing logging configuration"
