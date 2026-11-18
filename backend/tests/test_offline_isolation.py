"""Offline mode checked in independent processes, so global state of the pytest process cannot affect the result.

Each child process blocks and records every attempt to resolve a host name or open a connection *before* importing
anything else, so a network attempt is detected even when a network is available. The child environment is built
explicitly: HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE and HF_DATASETS_OFFLINE inherited from the parent are removed, so
these tests do not depend on how pytest itself was started.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
OFFLINE_VARIABLES = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")
HEAVY_MODULES = ("torch", "transformers", "sentence_transformers")

CHILD = r"""
import json, os, socket, sys

attempts = []

def _blocked(kind):
    def guard(*args, **kwargs):
        attempts.append(kind + " " + repr(args[1:] if kind == "connect" else args[:2]))
        raise OSError("network disabled in this test process")
    return guard

socket.getaddrinfo = _blocked("getaddrinfo")
socket.create_connection = _blocked("create_connection")
socket.socket.connect = _blocked("connect")
socket.socket.connect_ex = _blocked("connect")

mode, backend = sys.argv[1], sys.argv[2]
sys.path.insert(0, backend)
report = {"env_at_start": {k: os.environ.get(k) for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}}

if mode == "preimported":
    import huggingface_hub.constants
    report["offline_after_early_import"] = huggingface_hub.constants.is_offline_mode()

from app.engine import EngineConfigError, GraniteEmbedder
report["hub_loaded_before_init"] = "huggingface_hub" in sys.modules
try:
    embedder = GraniteEmbedder()
    vectors = embedder.encode(["casa", "perro"])
    report["result"] = "loaded"
    report["shape"] = list(vectors.shape)
    report["describe_offline"] = embedder.describe()["hf_hub_offline"]
except EngineConfigError as exc:
    report["result"] = "EngineConfigError"
    report["message"] = str(exc)

import huggingface_hub.constants
report["offline_effective"] = huggingface_hub.constants.is_offline_mode()
report["env_at_end"] = os.environ.get("HF_HUB_OFFLINE")
report["heavy_modules_loaded"] = sorted(m for m in ("torch", "transformers", "sentence_transformers") if m in sys.modules)
report["network_attempts"] = attempts
print("REPORT " + json.dumps(report))
"""


def run_child(mode: str, extra_env: dict[str, str] | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in OFFLINE_VARIABLES}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra_env or {})
    proc = subprocess.run([sys.executable, "-I", "-B", "-c", CHILD, mode, str(BACKEND)], env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=600)
    lines = [line for line in proc.stdout.splitlines() if line.startswith("REPORT ")]
    assert proc.returncode == 0 and lines, f"child failed (exit {proc.returncode}):\n{proc.stdout[-2000:]}\n{proc.stderr[-4000:]}"
    return json.loads(lines[-1][len("REPORT "):])


@pytest.mark.model
def test_case_a_normal_initialization_sets_offline_before_loading():
    report = run_child("normal")
    assert report["env_at_start"] == {"HF_HUB_OFFLINE": None, "TRANSFORMERS_OFFLINE": None}
    assert report["hub_loaded_before_init"] is False  # importing the engine does not import huggingface_hub
    assert report["result"] == "loaded" and report["shape"] == [2, 768]
    assert report["offline_effective"] is True and report["describe_offline"] is True
    assert report["env_at_end"] == "1"
    assert report["network_attempts"] == []


def test_case_b_huggingface_hub_imported_earlier_without_offline_fails_explicitly():
    report = run_child("preimported")
    assert report["env_at_start"] == {"HF_HUB_OFFLINE": None, "TRANSFORMERS_OFFLINE": None}
    assert report["offline_after_early_import"] is False
    assert report["result"] == "EngineConfigError"
    assert "not effectively active" in report["message"] and "before anything imports huggingface_hub" in report["message"]
    # The environment variable *is* "1" now, yet loading was refused: the check reads the effective library state.
    assert report["env_at_end"] == "1" and report["offline_effective"] is False
    assert report["heavy_modules_loaded"] == []  # refused before torch, transformers or the model were touched
    assert report["network_attempts"] == []


def test_case_b_offline_explicitly_disabled_fails_explicitly():
    report = run_child("normal", {"HF_HUB_OFFLINE": "0"})
    assert report["env_at_start"]["HF_HUB_OFFLINE"] == "0"
    assert report["result"] == "EngineConfigError" and "not effectively active" in report["message"]
    assert report["heavy_modules_loaded"] == []
    assert report["network_attempts"] == []
