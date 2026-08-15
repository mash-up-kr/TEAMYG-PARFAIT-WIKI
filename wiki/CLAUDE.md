# 파르페 정책 위키 운영 절차

## 목적

파르페 앱 화면별 정책(온보딩/캔버스/그룹목록/그룹사이드/앱사이드메뉴)에 대한 질문에, 근거 문서를 밝히며 답한다. 근거 없이 추측하지 않는다.

## 절차

1. 질문의 intent를 판단한다: `query`(질문 응답) / `ingest`(raw→wiki 반영) / `lint`(검증) / `add-domain`(도메인 추가) / `unclear`(모호하면 진행을 멈추고 사용자에게 되묻는다).
2. 관련 domain을 판단한다: `onboarding`, `canvas`, `group-list`, `group-side`, `app-side`. 여러 도메인에 걸치면 도메인마다 3단계를 반복한다.
3. 다음을 실행해 읽어야 할 파일 목록을 얻는다:

   ```
   python3 wiki/script/route.py --intent <intent> --domain <domain>
   ```

4. 위 목록에 있는 파일만 읽는다. 목록 밖의 파일은 읽지 않는다. 단 `external/`은 아래 예외를 따른다.

## `external/` 구현 레포 참조

`external/android`(TEAMYG-Android), `external/server`(TEAMYG-SERVER), `external/ios`(TEAMYG-iOS)는 플랫폼별 구현 레포를 git submodule로 연결한 **읽기 전용** 사본이다.

- 기본적으로 읽지 않는다. 3단계의 파일 목록에 포함되지 않으며, 정책 질문의 근거는 언제나 `wiki/domains/`다.
- 사용자가 구현과의 대조를 명시적으로 요청할 때만(예: "정책대로 구현됐는지 확인", "안드로이드 코드에선 어떻게 처리해?") 해당 플랫폼 디렉터리를 읽는다.
- 구현 코드는 **정책 근거가 아니다.** 코드를 인용할 때는 `<doc_code> §<절번호>` 인용과 구분해 `external/android/...:<line>` 형태의 파일 경로로 밝히고, "정책 문서 기준"과 "현재 구현 기준"을 명확히 나눠 서술한다.
- 정책과 구현이 어긋나면 어느 쪽이 옳은지 단정하지 말고 불일치 사실만 보고한다.
- `external/` 하위 파일은 절대 수정하지 않는다. 수정이 필요하면 해당 원본 레포에서 작업한다.
- 동기화는 `./wiki/script/sync-external.sh`로 한다. 자동으로 커밋하지 않는다.

## query 응답 규칙

- 인용은 `<doc_code> §<절번호>` 형식을 쓴다 (예: `SM-001 §3.2.4`). 절 번호가 없는 서술이면 `<doc_code>`만 쓴다. 상세 규칙은 `wiki/conventions.md` 참고.
- 단, `canvas` 도메인은 예외다. frontmatter의 `doc_code`를 그대로 쓰지 말고, 답변이 속한 문서 내부의 실제 정책 코드(`CAN-001`~`CAN-011` 중 해당하는 것)와 그 정책 자신의 §번호를 찾아 인용한다. `wiki/conventions.md`의 "canvas 인용 예외" 참고.
- 대상 도메인 문서에서 근거를 찾을 수 없으면 "정책 문서에서 찾을 수 없음"이라고 명확히 말한다. 일반 지식으로 대체 답변하지 않는다.
- 문서 frontmatter의 `status`가 `draft`이면 답하되 "(초안 상태, 팀 확정 전)"이라고 반드시 표시한다.
- 문서 안에서 스스로 "정책 아님 — 인용 금지"라고 표시한 섹션(예: 미확정 사항)은 정책 근거로 인용하지 않는다. 사용자가 미결/TODO 성격을 명시적으로 물으면 그 내용을 보여주되 "정책이 아니라 미결 사항"이라고 구분해서 안내한다.

## ingest 절차

1. `raw/<domain>/`의 원본을 읽는다.
2. `wiki/domains/<domain>.md`에 frontmatter(`title`/`domain`/`doc_code`/`status`/`source`/`updated`)를 붙이고, 원문 내용은 요약·재정리·수정 없이 그대로 옮긴다.
3. 결과를 자동으로 커밋하지 않는다. 변경 사항을 사람이 검토하도록 남겨둔다.

## lint 절차

```
python3 wiki/script/lint.py
```

결과를 그대로 보고한다. 실패해도 스스로 고치지 않고 무엇이 실패했는지 보고한다.

## add-domain 절차

1. `raw/<domain>/` 폴더를 만든다.
2. `wiki/routing.json`의 `domains` 배열에 추가한다.
3. `wiki/index.md`에 링크를 추가한다.
4. `wiki/conventions.md`의 도메인 코드 매핑 표에 `doc_code`를 추가한다.
