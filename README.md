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
wiki/script/sync-external.sh       # external/ 서브모듈 동기화 CLI
wiki/script/tests/                 # 위 스크립트들의 unittest
external/<platform>/               # 플랫폼별 구현 레포 (git submodule, 읽기 전용)
```

현재 도메인: `onboarding`, `canvas`, `group-list`, `group-side`, `app-side`.

## 연동된 구현 레포 (`external/`)

정책과 실제 구현을 교차 참조하기 위해 플랫폼 레포를 git submodule로 연결해 둡니다. **읽기 전용**이며, 이 저장소에서 수정하지 않습니다.

| 경로 | 원본 | 추적 브랜치 |
|---|---|---|
| `external/android` | [mash-up-kr/TEAMYG-Android](https://github.com/mash-up-kr/TEAMYG-Android) | `develop` |
| `external/server` | [mash-up-kr/TEAMYG-SERVER](https://github.com/mash-up-kr/TEAMYG-SERVER) | `main` |
| `external/ios` | [mash-up-kr/TEAMYG-iOS](https://github.com/mash-up-kr/TEAMYG-iOS) | `main` |

처음 클론할 때:

```
git clone --recurse-submodules <this-repo>
```

이미 클론했다면:

```
git submodule update --init --recursive
```

최신 커밋으로 동기화 (추적 브랜치 기준):

```
./wiki/script/sync-external.sh
```

동기화 후 서브모듈 포인터가 바뀌면 이 저장소에도 커밋해야 팀원에게 전파됩니다. 스크립트가 변경 여부와 커밋 명령을 안내합니다.

## 정책 ↔ 구현 대조 감사

`wiki/domains/`의 정책 규칙이 각 플랫폼에 실제로 구현되어 있는지 전수 대조하고 HTML 보고서를 만듭니다. Claude에게 요청하면 됩니다.

```
정책이랑 구현이랑 맞는지 대조해줘        (또는 /policy-impl-audit)
```

규칙마다 플랫폼별로 `맞게 구현` / `잘못 구현` / `미구현` / `대상 아님` 중 하나를 판정합니다. 보고서는 상단에 플랫폼별 요약 수치, 하단에 규칙별 근거(파일·줄 번호)를 담습니다.

결과물은 분석 **시작 시각** 기준으로 이름이 붙습니다.

```
reports/policy-audit-YYYYMMDD-HHMMSS.html
```

절차는 [`.claude/skills/policy-impl-audit/SKILL.md`](.claude/skills/policy-impl-audit/SKILL.md)에 정의되어 있고, 렌더링은 `render_report.py`가 담당합니다. 판정 근거가 없는 `맞게 구현`은 스크립트가 거부합니다.

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
