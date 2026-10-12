"""Explicit new TEST_ONLY replay request, native body and calendar; never normal app data."""

import argparse
import json
from pathlib import Path

from scripts.build_p19_test_evidence import calendar, request
from scripts.build_p28_test_inputs import AT, DAY, instrument, payload
from workers.daily.features import definitions

from alphalens_data.daily.contracts import Provider, Request
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--provider", choices=("upstox", "indstocks", "angel-one"), default="upstox"
    )
    args = parser.parse_args()
    root = args.root
    if not root.name.startswith("TEST_ONLY_") or root.exists():
        raise ValueError("NEW_TEST_ONLY_LOCATION_REQUIRED")
    root.mkdir(parents=True)
    native = payload(args.provider)
    identity = instrument(args.provider)
    body = {
        "version": "p28.test-provider.v1",
        "classification": "TEST_ONLY",
        "price_basis": "RAW_UNADJUSTED",
        "provider": args.provider,
        "native_payload_hex": native.hex(),
        "native_payload_sha256": checksum(native),
        "instruments": [identity.model_dump(mode="json")],
    }
    fixture = root / "bundle.json"
    fixture.write_bytes(stable_json(body))
    (root / "instruments.json").write_text(json.dumps([identity.model_dump(mode="json")]))
    known = calendar([DAY])
    changes = dict(
        session=DAY,
        source_received_at=AT,
        calendar=known,
        source_filename="TEST_ONLY_native.json",
        expected_security_ids=(identity.canonical_security_id,),
        feature_registry_id=checksum(
            stable_json([d.model_dump(mode="json") for d in definitions(DAY, AT)])
        ),
        provider=Provider(
            source=args.provider,
            dataset="test-only-nse",
            revision="TEST_ONLY",
            status="SOURCE_NOT_CLEARED",
            evidence_reference="TEST_ONLY_OFFLINE",
        ),
    )
    value = Request.model_validate({**request(fixture).model_dump(), **changes})
    (root / "request.json").write_bytes(stable_json(value.model_dump(mode="json")))
    (root / "calendar.json").write_bytes(stable_json(known.model_dump(mode="json")))
    print("TEST_ONLY_OFFLINE_INPUTS_CREATED_NO_ACQUISITION")


if __name__ == "__main__":
    main()
