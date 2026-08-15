#!/usr/bin/env python3
"""주어진 intent/domain에 대해 읽어야 할 위키 파일 목록을 계산한다."""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTING_PATH = REPO_ROOT / "wiki" / "routing.json"


def load_routing(routing_path: Path) -> dict:
    with routing_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_files(routing: dict, intent: str, domain, repo_root: Path) -> list:
    if intent not in routing["intents"]:
        raise ValueError(f"unknown intent: {intent}")

    patterns = routing["intents"][intent]["files"]
    needs_domain = any("{domain}" in pattern for pattern in patterns)

    if needs_domain and domain is None:
        raise ValueError(f"--domain is required for intent '{intent}'")

    if needs_domain and domain is not None and domain not in routing["domains"]:
        known = ", ".join(routing["domains"])
        raise ValueError(f"unknown domain: {domain!r} (known domains: {known})")

    resolved = []
    for pattern in patterns:
        filled = pattern.replace("{domain}", domain) if domain else pattern
        if "*" in filled:
            matches = sorted(
                str(p.relative_to(repo_root)) for p in repo_root.glob(filled)
            )
            resolved.extend(matches)
        else:
            resolved.append(filled)
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve which wiki files to read for an intent"
    )
    parser.add_argument(
        "--intent",
        required=True,
        choices=["query", "ingest", "lint", "add-domain", "unclear"],
    )
    parser.add_argument("--domain")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.intent == "unclear":
        print("intent is unclear — stop and ask the user to clarify", file=sys.stderr)
        return 1

    try:
        routing = load_routing(ROUTING_PATH)
        files = resolve_files(routing, args.intent, args.domain, REPO_ROOT)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(files))
    else:
        for f in files:
            print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
