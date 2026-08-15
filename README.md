# TEAMYG-PARFAIT-WIKI

파르페 앱의 화면별 정책을 도메인별로 정리한 위키 저장소입니다. Claude가 정책 질문에 답하거나, 원본 문서를 위키에 반영하거나, 문서 정합성을 검증할 때 이 저장소의 절차를 따릅니다.

## 사용 방법

사람은 스크립트를 직접 실행하지 않습니다. Claude에게 파르페 화면 정책을 자연어로 물어보면, Claude가 [`wiki/CLAUDE.md`](wiki/CLAUDE.md) 절차에 따라 intent(`query`/`ingest`/`lint`/`add-domain`)와 도메인을 판단하고, 내부적으로 `wiki/script/route.py`를 실행해 읽어야 할 파일 목록을 정한 뒤 근거 문서를 밝히며 답합니다.

예: "캔버스에서 토핑 배치 정책이 뭐야?", "raw/onboarding 원본을 위키에 반영해줘", "위키 정합성 검증해줘"

작업 절차 자체를 바꾸거나 도메인을 추가하려면 [`wiki/CLAUDE.md`](wiki/CLAUDE.md)를 직접 읽고 수정하세요.

## 디렉터리 구조

```
raw/<domain>/<domain>-policy.md   # 노션 등에서 가져온 원본 정책 문서 (사람만 수정)
wiki/domains/<domain>.md          # raw를 요약·수정 없이 옮긴 위키 문서 (frontmatter 포함)
wiki/index.md                     # 도메인 문서 허브 (링크 + 상태)
wiki/conventions.md               # frontmatter 규칙, 인용 규칙, 파일명 규칙
wiki/routing.json                 # intent/domain별로 읽어야 할 파일 목록 정의
wiki/script/route.py              # routing.json을 바탕으로 파일 목록을 계산하는 CLI
wiki/script/lint.py                # 위키 문서 정합성 검증 CLI
wiki/script/tests/                 # 위 스크립트들의 unittest
```

현재 도메인: `onboarding`, `canvas`, `group-list`, `group-side`, `app-side`.

## 스크립트 (내부 도구 / 수동 검증용)

`wiki/script/route.py`는 Claude가 질문마다 내부적으로 호출하는 라우팅 도구입니다. 사람이 직접 쓸 일은 거의 없지만, 디버깅 시 아래처럼 확인할 수 있습니다.

```
python3 wiki/script/route.py --intent <intent> --domain <domain>
```

`lint.py`는 `wiki/domains/*.md`의 frontmatter·규칙 위반을 검증합니다. 위키 문서를 고친 뒤 커밋 전에 사람이 직접 돌려서 확인하는 용도입니다.

```
python3 wiki/script/lint.py
```

스크립트 테스트 실행:

```
python3 -m unittest discover -s wiki/script/tests
```

## 문서 반영(ingest) 규칙

`raw/<domain>/`의 원본을 `wiki/domains/<domain>.md`로 옮길 때는 frontmatter(`title`/`domain`/`doc_code`/`status`/`source`/`updated`)만 붙이고, 본문은 요약·재정리·수정 없이 그대로 옮깁니다. 반영 결과는 자동으로 커밋하지 않고 사람이 검토합니다. 자세한 규칙은 [`wiki/conventions.md`](wiki/conventions.md) 참고.
