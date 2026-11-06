"""TEST_ONLY runtime parity and failure injection; never market predictions."""

import importlib
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from workers.nse_market import sequence
from workers.nse_market import sequence_runtime as runtime


@pytest.fixture
def model() -> dict[str, Any]:
    rng = np.random.default_rng(1729)
    return {
        "family": sequence.FAMILY,
        "feature_version": sequence.VERSION,
        "feature_names": list(sequence.NAMES),
        "sequence_length": sequence.LENGTH,
        "mean": [0.1] * 8,
        "scale": [1.2] * 8,
        "state": {
            "0.weight_ih_l0": rng.normal(0, 0.1, (64, 8)).tolist(),
            "0.weight_hh_l0": rng.normal(0, 0.1, (64, 16)).tolist(),
            "0.bias_ih_l0": rng.normal(0, 0.1, 64).tolist(),
            "0.bias_hh_l0": rng.normal(0, 0.1, 64).tolist(),
            "2.weight": rng.normal(0, 0.1, (1, 16)).tolist(),
            "2.bias": [0.03],
        },
    }


def test_cpu_batch_order_and_exact_saved_equations(model: dict[str, Any]) -> None:
    values = np.random.default_rng(19).normal(size=(17, 20, 8))
    result, info = runtime.predict(model, values, batch_size=3)
    assert np.allclose(result, sequence.predict(model, values), atol=1e-15, rtol=0)
    assert info["sequences"] == 17 and info["completed_device"] == "cpu"
    assert info["capability"] is None and info["fallback_reason"] is None
    assert info["production_predictor_changed"] is False


@pytest.mark.parametrize("device", ["auto", "cuda", "xpu"])
def test_unavailable_device_cpu_fallback(
    model: dict[str, Any], monkeypatch: pytest.MonkeyPatch, device: str
) -> None:
    monkeypatch.setattr(
        runtime,
        "capability",
        lambda: {
            "cuda_available": False,
            "xpu_available": False,
            "torch_version": None,
        },
    )
    result, info = runtime.predict(model, np.zeros((2, 20, 8)), device=device)
    assert np.array_equal(result, sequence.predict(model, np.zeros((2, 20, 8))))
    assert info["fallback_reason"] == "REQUESTED_ACCELERATOR_UNAVAILABLE"


@pytest.mark.parametrize("case", ["oom", "parity", "memory", "memory_unknown", "success"])
def test_simulated_accelerator_guards(
    model: dict[str, Any], monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    monkeypatch.setattr(
        runtime,
        "capability",
        lambda: {
            "cuda_available": True,
            "xpu_available": False,
        },
    )

    def memory() -> tuple[int, int]:
        if case == "memory_unknown":
            raise NotImplementedError
        return (0 if case == "memory" else 16 * 1024 * 1024, 32 * 1024 * 1024)

    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda _: SimpleNamespace(
            cuda=SimpleNamespace(mem_get_info=memory),
        ),
    )
    calls = []

    def accelerated(m: dict[str, Any], values: Any, device: str) -> Any:
        calls.append(len(values))
        if case == "oom":
            raise RuntimeError("TEST_ONLY_OOM")
        return sequence.predict(m, values) + (0.1 if case == "parity" else 0)

    monkeypatch.setattr(runtime, "_accelerated", accelerated)
    values = np.zeros((5, 20, 8))
    result, info = runtime.predict(model, values, device="auto", batch_size=2)
    assert np.array_equal(result, sequence.predict(model, values))
    assert info["completed_device"] == ("cuda" if case == "success" else "cpu")
    if case.startswith("memory"):
        assert calls == []
    elif case == "success":
        assert calls == [2, 2, 1] and info["accelerator_batches"] == 3
    else:
        assert calls == [2] and info["fallback_reason"] is not None


def test_missing_features_and_invalid_model_never_become_fallback(
    model: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden() -> Any:
        raise AssertionError("MUST_VALIDATE_BEFORE_ACCELERATOR_PROBE")

    monkeypatch.setattr(runtime, "capability", forbidden)
    for values in (np.zeros((2, 19, 8)), np.full((2, 20, 8), np.nan)):
        with pytest.raises(ValueError, match="ORDERED_SEQUENCE"):
            runtime.predict(model, values, device="auto")
    with pytest.raises(ValueError, match="SCALING"):
        runtime.predict({**model, "scale": [0] * 8}, np.zeros((1, 20, 8)), device="auto")


@pytest.mark.parametrize(
    "options",
    [
        {"device": "untrusted"},
        {"batch_size": 0},
        {"batch_size": 4097},
        {"batch_size": True},
        {"working_bytes": 0},
        {"working_bytes": 256 * 1024 * 1024},
    ],
)
def test_configuration_bounds(model: dict[str, Any], options: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="REQUIRED"):
        runtime.predict(model, np.zeros((1, 20, 8)), **options)


def test_empty_batch_and_memory_bound(model: dict[str, Any]) -> None:
    values, info = runtime.predict(model, np.empty((0, 20, 8)), device="auto")
    assert len(values) == 0 and info["accelerator_batches"] == 0
    _, info = runtime.predict(model, np.zeros((1, 20, 8)), batch_size=4096, working_bytes=1048576)
    assert info["batch_size"] == 128


def test_probe_driver_failure_is_unavailable_not_a_process_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed() -> bool:
        raise RuntimeError("TEST_ONLY_DRIVER_FAILURE")

    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda _: SimpleNamespace(
            __version__="TEST_ONLY",
            cuda=SimpleNamespace(is_available=failed),
            xpu=SimpleNamespace(is_available=lambda: False),
        ),
    )
    assert runtime.capability() == {
        "torch_version": "TEST_ONLY",
        "cuda_available": False,
        "xpu_available": False,
    }


def test_optional_real_torch_equations(model: dict[str, Any]) -> None:
    pytest.importorskip("torch", reason="optional PyTorch environment; not a GPU pass")
    values = np.random.default_rng(3).normal(size=(7, 20, 8))
    assert np.allclose(
        runtime._accelerated(model, values, "cpu"),
        sequence.predict(model, values),
        rtol=0,
        atol=1e-10,
    )
