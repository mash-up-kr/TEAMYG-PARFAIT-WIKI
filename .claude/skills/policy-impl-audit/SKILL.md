---
name: policy-impl-audit
description: wiki/domains 의 정책 규칙과 external/ 의 플랫폼 구현(Android/iOS/Server)을 전수 대조해 불일치 보고서(HTML)를 만든다. "정책 구현 대조", "구현 감사", "정책대로 구현됐는지 확인", "audit", "불일치 보고서" 등의 요청 시 사용.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
---

# 정책 ↔ 구현 대조 감사

`wiki/domains/*.md`에 정의된 정책 규칙 하나하나가 `external/`의 각 플랫폼 레포에 실제로 구현되어 있는지 **전수 조사**하고, 결과를 HTML 보고서로 낸다.

이 스킬은 `wiki/CLAUDE.md`가 규정한 "`external/`은 사용자가 구현 대조를 명시적으로 요청할 때만 읽는다"의 **그 명시적 요청에 해당한다.** 따라서 `external/` 하위를 읽어도 된다. 단 **절대 수정하지 않는다.**

## 0. 시작 시각 고정

가장 먼저 시작 시각을 찍고 끝까지 이 값을 쓴다. 보고서 파일명의 기준이다.

```
date +%Y-%m-%dT%H:%M:%S
```

## 1. 구현 레포 최신화 (먼저 한다)

대조하기 전에 **항상** 세 레포를 각자의 추적 브랜치 최신으로 올린다. 묻지 말고 그냥 실행한다. 낡은 코드로 "미구현" 판정을 내면 보고서 전체가 틀린다.

```
./wiki/script/sync-external.sh
```

실행 후 반드시 확인한다.

```
git submodule status
```

- 세 줄이 모두 나오지 않으면(서브모듈 미초기화) 진행하지 않고 사용자에게 알린다.
- 동기화로 포인터가 바뀌었으면 그 사실과 이전→이후 SHA를 기억해 두고, 5단계 JSON의 `submodules`에 **최신 SHA**를 기록한다. 보고서가 어느 시점 코드를 본 것인지 남아야 한다.
- 네트워크 실패로 동기화가 안 되면 그대로 진행하되, 어느 레포가 갱신되지 않았는지 사용자에게 밝히고 보고서 `submodules`에도 그 SHA를 적는다.
- 동기화 결과를 **커밋하지 않는다.** 포인터 변경은 사용자가 검토한다.

## 2. 대조 대상 파악

```
python3 wiki/script/route.py --intent lint
```

여기서 나온 `wiki/domains/*.md`가 대조 대상 전부다.

## 3. 규칙 추출

각 도메인 문서에서 **검증 가능한 규칙**만 뽑는다.

- 대상은 `## 3. 규칙` 절의 `- **3.2.4** ...` 형태 항목이다. canvas는 `CAN-001`~`CAN-011` 각 정책의 `### 3. 규칙`을 각각 처리한다.
- 규칙 ID는 `wiki/conventions.md`의 인용 규칙을 그대로 따른다 (`SM-001 §3.2.4`). **canvas는 frontmatter의 `doc_code`를 쓰지 말고** 해당 정책 코드를 쓴다 (`CAN-004 §3.2`).
- **제외할 것**: `## 8. 미확정 사항 (정책 아님 — 인용 금지)` 같이 문서가 스스로 정책이 아니라고 밝힌 절, `## 4. 예시`, `## 6. 문구 표`(단, 규칙이 문구 표를 참조하면 그 규칙의 검증 근거로는 쓴다).
- 한 규칙이 여러 동작을 담고 있으면 쪼개지 말고 하나로 둔다. 규칙 번호가 보고서의 추적 단위다.

규칙을 빠뜨리지 않는다. **전수 조사가 이 스킬의 목적이다.** 규칙 수를 도메인별로 세어두고 마지막에 보고서의 규칙 수와 일치하는지 검산한다.

## 4. 플랫폼별 대조

플랫폼별 탐색 시작점:

| 플랫폼 | 경로 | 주로 볼 것 |
|---|---|---|
| Android | `external/android` | `feature/`(화면·ViewModel·Compose), `domain/`, `data/` |
| iOS | `external/ios/Parfait` | 화면 View, ViewModel, 모델 |
| Server | `external/server` | `core/`(도메인 로직), `bootstrap/`(API), `persistence/` |

규칙마다 세 플랫폼 각각에 대해 하나를 판정한다.

| 판정 | 뜻 | 조건 |
|---|---|---|
| `match` | 맞게 구현됨 | 규칙대로 동작하는 코드를 찾았다 |
| `mismatch` | 잘못 구현됨 | 구현은 있는데 규칙과 다르게 동작한다 (값·조건·순서·문구 불일치) |
| `missing` | 미구현 | 해당 기능 코드가 아예 없다 |
| `na` | 대상 아님 | 그 플랫폼의 책임이 아니다 (예: 순수 UI 규칙에 대한 Server) |

판정 원칙:

- **근거 없으면 `match`로 적지 않는다.** 파일 경로와 줄 번호를 `evidence`에 남기지 못하면 `match`가 아니다.
- `missing`과 `na`를 구분한다. 서버가 구현할 이유가 없는 UI 문구 규칙은 `missing`이 아니라 `na`다. 이걸 뭉개면 미구현 수치가 부풀어 보고서가 쓸모없어진다.
- 검색은 최소 두 갈래로 한다. 화면·기능 이름으로 한 번, 규칙의 구체값(글자수 제한, 타임아웃 초, 문구 리터럴 등)으로 한 번. 한쪽만 보고 `missing`으로 단정하지 않는다.
- 확신이 서지 않으면 `confidence`를 `low`로 두고 `note`에 무엇을 확인하지 못했는지 쓴다. 추측으로 단정하는 것보다 낫다.
- 문서 `status`가 `draft`인 도메인은 규칙 자체가 확정 전이다. 판정은 하되 보고서에 draft로 표시된다(스크립트가 처리).
- 정책과 구현이 어긋날 때 **어느 쪽이 옳은지 판단하지 않는다.** 불일치 사실과 양쪽 내용만 적는다.

## 5. 결과 JSON 작성

`/tmp` 등 작업 경로에 findings JSON을 쓴다. 스키마:

```json
{
  "started_at": "2026-08-15T16:10:33",
  "repo": "TEAMYG-PARFAIT-WIKI",
  "submodules": {
    "android": "ca9e458 (develop)",
    "ios": "10ddda7 (main)",
    "server": "a0779b1 (main)"
  },
  "domains": [
    {
      "domain": "app-side",
      "title": "앱 사이드메뉴 정책",
      "doc_code": "SM-001",
      "status": "draft",
      "rules": [
        {
          "rule_id": "SM-001 §3.2.4",
          "text": "닉네임에 연속된 공백 2칸 이상을 허용하지 않는다.",
          "platforms": {
            "android": {
              "verdict": "mismatch",
              "confidence": "high",
              "evidence": ["external/android/feature/groups/.../NicknameValidator.kt:31"],
              "note": "연속 공백 검사가 없고 trim 만 수행한다."
            },
            "ios":     { "verdict": "missing", "confidence": "medium", "evidence": [], "note": "닉네임 수정 화면을 찾지 못했다." },
            "server":  { "verdict": "na", "confidence": "high", "evidence": [], "note": "클라이언트 입력 검증 규칙이다." }
          }
        }
      ]
    }
  ]
}
```

`verdict`는 반드시 `match|mismatch|missing|na` 중 하나, `confidence`는 `high|medium|low`다.

## 6. 보고서 렌더링

```
python3 .claude/skills/policy-impl-audit/render_report.py --findings <json경로> --out-dir reports
```

스크립트가 `started_at`을 기준으로 `reports/policy-audit-YYYYMMDD-HHMMSS.html`을 만들고 경로를 출력한다. 스키마가 틀리면 실패하니 오류 메시지대로 JSON을 고쳐 다시 돌린다.

렌더링 후:

- 규칙 수가 3단계에서 센 값과 같은지 검산한다.
- 사용자에게 보고서 경로와 함께 플랫폼별 요약 수치를 알린다.
- **자동으로 커밋하지 않는다.**

## 보고할 때

숫자만 나열하지 말고 다음을 짚는다.

- 플랫폼별 `mismatch` 중 영향이 큰 것 몇 개
- 세 플랫폼 모두 `missing`인 규칙 (정책만 있고 아무도 구현 안 한 것)
- 한 플랫폼만 다르게 구현된 규칙 (플랫폼 간 동작 불일치)
- `confidence: low`가 많은 영역 — 보고서 신뢰도의 한계로 반드시 밝힌다
