"""Opt-in numeric LSTM execution; no fitting, provider calls or publication.

The existing production predictor remains unchanged. Accelerator output is accepted
only after parity with the reviewed float64 gate equations. No pickle is loaded.
"""

from __future__ import annotations

import importlib
import time
from typing import Any

import numpy as np

from workers.nse_market import sequence

MAX_INPUT_BYTES = 128 * 1024 * 1024
BYTES_PER_SEQUENCE = 8192  # conservative working-tensor envelope for 20x8/16 hidden state


def capability() -> dict[str, Any]:
    """Explicit diagnostic only. Dashboard reads saved results, never imports torch."""
    try:
        torch = importlib.import_module("torch")
    except (ImportError, OSError):
        return {"torch_version": None, "cuda_available": False, "xpu_available": False}

    def available(name: str) -> bool:
        try:
            return bool(hasattr(torch, name) and getattr(torch, name).is_available())
        except (RuntimeError, NotImplementedError, OSError):
            return False

    return {
        "torch_version": str(torch.__version__),
        "cuda_available": available("cuda"),
        "xpu_available": available("xpu"),
    }


def _accelerated(model: dict[str, Any], matrix: Any, device: str) -> Any:
    """Same fixed float64 gates as sequence.predict; device tensors stay batch-bounded."""
    torch = importlib.import_module("torch")
    with torch.inference_mode():

        def tensor(value: Any) -> Any:
            return torch.as_tensor(value, dtype=torch.float64, device=device)

        values = (tensor(matrix) - tensor(model["mean"])) / tensor(model["scale"])
        state = {key: tensor(value) for key, value in model["state"].items()}
        hidden = torch.zeros((len(matrix), 16), dtype=torch.float64, device=device)
        cell = hidden.clone()
        for step in range(sequence.LENGTH):
            gates = (
                values[:, step] @ state["0.weight_ih_l0"].T
                + hidden @ state["0.weight_hh_l0"].T
                + state["0.bias_ih_l0"]
                + state["0.bias_hh_l0"]
            )
            ingate, forget, candidate, outgate = gates.chunk(4, dim=1)
            cell = torch.sigmoid(forget) * cell + torch.sigmoid(ingate) * torch.tanh(candidate)
            hidden = torch.sigmoid(outgate) * torch.tanh(cell)
        return torch.sigmoid(hidden @ state["2.weight"].T + state["2.bias"])[:, 0].cpu().numpy()


def predict(
    model: dict[str, Any],
    values: Any,
    *,
    device: str = "cpu",
    batch_size: int = 256,
    working_bytes: int = 32 * 1024 * 1024,
) -> tuple[Any, dict[str, Any]]:
    """Bounded, ordered inference with explicit CPU fallback; never persist scores.

    CPU is deliberately the default. ``auto``/``cuda``/``xpu`` are explicit opt-ins.
    Invalid inputs fail before device selection; fallback never fills missing data.
    """
    if device not in {"cpu", "auto", "cuda", "xpu"}:
        raise ValueError("REVIEWED_SEQUENCE_DEVICE_REQUIRED")
    if type(batch_size) is not int or not 1 <= batch_size <= 4096:
        raise ValueError("BOUNDED_SEQUENCE_BATCH_REQUIRED")
    if type(working_bytes) is not int or not 1024 * 1024 <= working_bytes <= MAX_INPUT_BYTES:
        raise ValueError("BOUNDED_SEQUENCE_MEMORY_REQUIRED")
    matrix = np.asarray(values, dtype=np.float64)
    if (
        matrix.ndim != 3
        or matrix.shape[1:] != (sequence.LENGTH, len(sequence.NAMES))
        or not np.isfinite(matrix).all()
        or matrix.nbytes > MAX_INPUT_BYTES
    ):
        raise ValueError("BOUNDED_COMPLETE_FINITE_ORDERED_SEQUENCE_REQUIRED")
    # Reuse the authoritative schema/scaler/state validator without evaluating inputs twice.
    sequence.predict(model, np.empty((0, sequence.LENGTH, len(sequence.NAMES))))
    selected, reason, caps = "cpu", None, None
    limit = min(batch_size, working_bytes // BYTES_PER_SEQUENCE)
    if device != "cpu" and len(matrix):
        caps = capability()
        available = [name for name in ("cuda", "xpu") if caps[f"{name}_available"]]
        chosen = available[0] if device == "auto" and available else device
        if chosen not in available:
            reason = "REQUESTED_ACCELERATOR_UNAVAILABLE"
        else:
            torch = importlib.import_module("torch")
            backend = getattr(torch, chosen)
            try:
                free, _ = backend.mem_get_info()
                limit = min(limit, int(free) // 4 // BYTES_PER_SEQUENCE)
                if limit < 1:
                    reason = "ACCELERATOR_MEMORY_HEADROOM_UNAVAILABLE"
                else:
                    selected = chosen
            except (RuntimeError, NotImplementedError, AttributeError):
                reason = "ACCELERATOR_MEMORY_EVIDENCE_UNAVAILABLE"
    limit = max(1, limit)
    started = time.perf_counter()
    output = []
    accelerator_batches = 0
    for offset in range(0, len(matrix), limit):
        batch = matrix[offset : offset + limit]
        if selected == "cpu":
            output.append(sequence.predict(model, batch))
            continue
        try:
            result = _accelerated(model, batch, selected)
            # Full batch parity, including classification boundary. Speed is not a safety gate.
            reference = sequence.predict(model, batch)
            if (
                result.shape != reference.shape
                or not np.isfinite(result).all()
                or not np.allclose(result, reference, rtol=0, atol=1e-10)
                or not np.array_equal(result >= 0.5, reference >= 0.5)
            ):
                selected, reason = "cpu", "ACCELERATOR_PARITY_REJECTED"
                result = reference
            else:
                accelerator_batches += 1
        except (RuntimeError, NotImplementedError):
            selected, reason = "cpu", "ACCELERATOR_EXECUTION_FAILED"
            result = sequence.predict(model, batch)
        output.append(result)
    elapsed = time.perf_counter() - started
    return (np.concatenate(output) if output else np.empty(0)), {
        "requested_device": device,
        "completed_device": selected,
        "accelerator_batches": accelerator_batches,
        "mixed_execution": accelerator_batches > 0 and selected == "cpu",
        "fallback_reason": reason,
        "capability": caps,
        "batch_size": limit,
        "sequences": len(matrix),
        "elapsed_seconds": elapsed,
        "sequences_per_second": len(matrix) / elapsed if elapsed > 0 else None,
        "parity_policy": "FULL_BATCH_FLOAT64_1e-10_AND_CLASS_BOUNDARY",
        "production_predictor_changed": False,
    }
