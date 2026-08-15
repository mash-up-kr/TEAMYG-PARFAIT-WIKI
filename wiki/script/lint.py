#!/usr/bin/env python3
"""wiki/domains/*.md가 wiki/conventions.md의 데이터 계약을 지키는지 검증한다."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTING_PATH = REPO_ROOT / "wiki" / "routing.json"

REQUIRED_FIELDS = ["title", "domain", "doc_code", "status", "source", "updated"]


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    block = text[4:end]
    fields = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def check_domains(routing: dict, repo_root: Path) -> list:
    errors = []
    for domain in routing["domains"]:
        doc_path = repo_root / "wiki" / "domains" / f"{domain}.md"
        if not doc_path.exists():
            errors.append(f"missing wiki/domains/{domain}.md for domain '{domain}'")
            continue

        text = doc_path.read_text(encoding="utf-8")
        fields = parse_frontmatter(text)
        for field in REQUIRED_FIELDS:
            if field not in fields or not fields[field]:
                errors.append(
                    f"wiki/domains/{domain}.md: missing frontmatter field '{field}'"
                )
        if "domain" in fields and fields["domain"] != domain:
            errors.append(
                f"wiki/domains/{domain}.md: frontmatter domain '{fields['domain']}' "
                f"does not match filename '{domain}'"
            )
        if fields.get("source"):
            if not (repo_root / fields["source"]).exists():
                errors.append(
                    f"wiki/domains/{domain}.md: source '{fields['source']}' does not exist"
                )
    return errors


def check_index_links(routing: dict, repo_root: Path) -> list:
    index_path = repo_root / "wiki" / "index.md"
    if not index_path.exists():
        return ["wiki/index.md does not exist"]
    text = index_path.read_text(encoding="utf-8")
    errors = []
    for domain in routing["domains"]:
        if domain not in text:
            errors.append(f"wiki/index.md does not link domain '{domain}'")
    return errors


def main() -> int:
    try:
        with ROUTING_PATH.open("r", encoding="utf-8") as f:
            routing = json.load(f)

        errors = check_domains(routing, REPO_ROOT) + check_index_links(routing, REPO_ROOT)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
