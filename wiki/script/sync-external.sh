#!/usr/bin/env bash
# external/ 하위 서브모듈을 각자의 추적 브랜치 최신 커밋으로 동기화한다.
# .gitmodules의 branch 값(android=develop, server=main, ios=main)을 따른다.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "== 서브모듈 초기화 =="
git submodule update --init --recursive

echo
echo "== 원격 최신 커밋으로 갱신 =="
git submodule update --remote --recursive

echo
echo "== 현재 상태 =="
git submodule status

echo
if git diff --quiet -- external; then
  echo "변경 없음 — 이미 최신입니다."
else
  echo "서브모듈 포인터가 변경되었습니다. 검토 후 커밋하세요:"
  git diff --submodule=log -- external
  echo
  echo "  git add external && git commit -m 'chore: external 서브모듈 동기화'"
fi
