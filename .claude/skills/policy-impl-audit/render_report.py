#!/usr/bin/env python3
"""정책↔구현 대조 findings JSON을 자체 완결형 HTML 보고서로 렌더링한다.

사용법:
    python3 render_report.py --findings findings.json --out-dir reports

보고서 파일명은 findings의 `started_at`(분석 시작 시각)을 기준으로 만든다.
"""
import argparse
import html
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PLATFORMS = [("android", "Android"), ("ios", "iOS"), ("server", "Server")]
VERDICTS = ["match", "mismatch", "missing", "na"]
VERDICT_LABEL = {
    "match": "맞게 구현",
    "mismatch": "잘못 구현",
    "missing": "미구현",
    "na": "대상 아님",
}
CONFIDENCE = ["high", "medium", "low"]


# ---------------------------------------------------------------- validation

def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def validate(data: dict) -> None:
    if not isinstance(data, dict):
        fail("최상위는 object여야 한다")
    for key in ("started_at", "domains"):
        if key not in data:
            fail(f"최상위에 '{key}'가 없다")
    try:
        datetime.strptime(data["started_at"], "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        fail("started_at 형식은 YYYY-MM-DDTHH:MM:SS 여야 한다 (예: 2026-08-15T16:10:33)")
    if not isinstance(data["domains"], list) or not data["domains"]:
        fail("domains는 비어 있지 않은 배열이어야 한다")

    for di, dom in enumerate(data["domains"]):
        where = f"domains[{di}]"
        for key in ("domain", "rules"):
            if key not in dom:
                fail(f"{where}에 '{key}'가 없다")
        if not isinstance(dom["rules"], list):
            fail(f"{where}.rules는 배열이어야 한다")
        for ri, rule in enumerate(dom["rules"]):
            rwhere = f"{where}.rules[{ri}]"
            for key in ("rule_id", "text", "platforms"):
                if key not in rule:
                    fail(f"{rwhere}에 '{key}'가 없다")
            plats = rule["platforms"]
            if not isinstance(plats, dict):
                fail(f"{rwhere}.platforms는 object여야 한다")
            for pkey, _ in PLATFORMS:
                if pkey not in plats:
                    fail(f"{rwhere}.platforms에 '{pkey}'가 없다 (세 플랫폼 모두 필요)")
                entry = plats[pkey]
                if not isinstance(entry, dict):
                    fail(f"{rwhere}.platforms.{pkey}는 object여야 한다")
                verdict = entry.get("verdict")
                if verdict not in VERDICTS:
                    fail(
                        f"{rwhere}.platforms.{pkey}.verdict='{verdict}' — "
                        f"{'|'.join(VERDICTS)} 중 하나여야 한다"
                    )
                conf = entry.get("confidence", "high")
                if conf not in CONFIDENCE:
                    fail(
                        f"{rwhere}.platforms.{pkey}.confidence='{conf}' — "
                        f"{'|'.join(CONFIDENCE)} 중 하나여야 한다"
                    )
                ev = entry.get("evidence", [])
                if not isinstance(ev, list):
                    fail(f"{rwhere}.platforms.{pkey}.evidence는 배열이어야 한다")
                if verdict == "match" and not ev:
                    fail(
                        f"{rwhere}.platforms.{pkey}: verdict가 'match'인데 evidence가 비었다. "
                        "근거 없는 match는 허용하지 않는다"
                    )


# ------------------------------------------------------------------ counting

def tally(data: dict) -> dict:
    per_platform = {p: Counter() for p, _ in PLATFORMS}
    for dom in data["domains"]:
        for rule in dom["rules"]:
            for pkey, _ in PLATFORMS:
                per_platform[pkey][rule["platforms"][pkey]["verdict"]] += 1
    return per_platform


# ------------------------------------------------------------------ rendering

def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def bar(counts: Counter) -> str:
    total = sum(counts.values()) or 1
    segs = []
    for v in VERDICTS:
        n = counts.get(v, 0)
        if n:
            pct = n / total * 100
            segs.append(
                f'<span class="seg v-{v}" style="width:{pct:.4f}%" '
                f'title="{VERDICT_LABEL[v]} {n}건"></span>'
            )
    return f'<div class="bar">{"".join(segs)}</div>'


def platform_card(pkey: str, plabel: str, counts: Counter) -> str:
    total = sum(counts.values())
    checked = total - counts.get("na", 0)
    ok = counts.get("match", 0)
    rate = (ok / checked * 100) if checked else 0.0
    cells = "".join(
        f'<div class="stat v-{v}"><span class="num">{counts.get(v, 0)}</span>'
        f'<span class="lbl">{VERDICT_LABEL[v]}</span></div>'
        for v in VERDICTS
    )
    return f"""<section class="card">
  <header class="card-head">
    <h3>{esc(plabel)}</h3>
    <span class="rate" title="대상 아님을 뺀 {checked}건 중 맞게 구현된 비율">{rate:.0f}%</span>
  </header>
  {bar(counts)}
  <div class="stats">{cells}</div>
</section>"""


def evidence_list(entry: dict) -> str:
    ev = entry.get("evidence") or []
    note = entry.get("note")
    parts = []
    if note:
        parts.append(f'<p class="note">{esc(note)}</p>')
    if ev:
        items = "".join(f"<li><code>{esc(e)}</code></li>" for e in ev)
        parts.append(f'<ul class="ev">{items}</ul>')
    if not parts:
        parts.append('<p class="note muted">기록된 근거 없음</p>')
    return "".join(parts)


def rule_block(rule: dict) -> str:
    verdicts = {p: rule["platforms"][p]["verdict"] for p, _ in PLATFORMS}
    classes = " ".join(f"has-{v}" for v in set(verdicts.values()))
    lows = [
        p for p, _ in PLATFORMS
        if rule["platforms"][p].get("confidence", "high") == "low"
    ]
    low_flag = (
        f'<span class="lowconf" title="확신도 낮음: {esc(", ".join(lows))}">확신도 낮음</span>'
        if lows else ""
    )

    pills = "".join(
        f'<span class="pill v-{verdicts[p]}">{esc(plabel)} · {VERDICT_LABEL[verdicts[p]]}</span>'
        for p, plabel in PLATFORMS
    )
    details = "".join(
        f"""<div class="pdetail">
      <div class="phead"><span class="dot v-{verdicts[p]}"></span>{esc(plabel)}
        <span class="conf c-{esc(rule['platforms'][p].get('confidence', 'high'))}">
          {esc(rule['platforms'][p].get('confidence', 'high'))}</span></div>
      {evidence_list(rule['platforms'][p])}
    </div>"""
        for p, plabel in PLATFORMS
    )

    return f"""<details class="rule {classes}">
  <summary>
    <div class="rsum">
      <code class="rid">{esc(rule['rule_id'])}</code>
      <span class="rtext">{esc(rule['text'])}</span>
      {low_flag}
    </div>
    <div class="pills">{pills}</div>
  </summary>
  <div class="pdetails">{details}</div>
</details>"""


def domain_section(dom: dict) -> str:
    counts = Counter()
    for rule in dom["rules"]:
        for p, _ in PLATFORMS:
            counts[rule["platforms"][p]["verdict"]] += 1
    draft = (
        '<span class="draft">초안 상태, 팀 확정 전</span>'
        if dom.get("status") == "draft" else ""
    )
    code = f'<code>{esc(dom["doc_code"])}</code>' if dom.get("doc_code") else ""
    rules = "".join(rule_block(r) for r in dom["rules"])
    return f"""<section class="domain">
  <h3>{esc(dom.get('title') or dom['domain'])} {code} {draft}
    <span class="cnt">규칙 {len(dom['rules'])}개</span></h3>
  {bar(counts)}
  <div class="rules">{rules}</div>
</section>"""


CSS = """
:root{--bg:#fbfbfd;--fg:#1b1b20;--muted:#6b6b78;--line:#e3e3ea;--card:#fff;
--match:#1a7f4b;--mismatch:#c62f3b;--missing:#b26a00;--na:#8a8a97;
--match-bg:#e8f5ee;--mismatch-bg:#fdeaec;--missing-bg:#fdf3e2;--na-bg:#f0f0f3;}
:root:not([data-theme=light]) {}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#131317;--fg:#e9e9ef;--muted:#9a9aa8;--line:#2c2c34;--card:#1b1b21;
--match:#5ad18f;--mismatch:#ff8b95;--missing:#ffc266;--na:#9a9aa8;
--match-bg:#14301f;--mismatch-bg:#3a1a1e;--missing-bg:#3a2c14;--na-bg:#25252c;}}
:root[data-theme=dark]{--bg:#131317;--fg:#e9e9ef;--muted:#9a9aa8;--line:#2c2c34;--card:#1b1b21;
--match:#5ad18f;--mismatch:#ff8b95;--missing:#ffc266;--na:#9a9aa8;
--match-bg:#14301f;--mismatch-bg:#3a1a1e;--missing-bg:#3a2c14;--na-bg:#25252c;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Pretendard","Apple SD Gothic Neo",
"Noto Sans KR",Segoe UI,sans-serif;}
.wrap{max-width:1120px;margin:0 auto;padding:40px 20px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:19px;margin:44px 0 14px;letter-spacing:-.01em}
h3{font-size:16px;margin:0}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em}
.meta{color:var(--muted);font-size:13px;margin:0 0 4px}
.meta code{background:var(--na-bg);padding:1px 6px;border-radius:5px}
.cards{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}
.rate{font-size:22px;font-weight:650;letter-spacing:-.02em}
.bar{display:flex;height:8px;border-radius:99px;overflow:hidden;background:var(--na-bg);margin-bottom:12px}
.seg{display:block;height:100%}
.seg.v-match{background:var(--match)}.seg.v-mismatch{background:var(--mismatch)}
.seg.v-missing{background:var(--missing)}.seg.v-na{background:var(--na);opacity:.45}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.stat{text-align:center;padding:8px 4px;border-radius:8px;background:var(--na-bg)}
.stat.v-match{background:var(--match-bg)}.stat.v-mismatch{background:var(--mismatch-bg)}
.stat.v-missing{background:var(--missing-bg)}
.stat .num{display:block;font-size:19px;font-weight:650}
.stat.v-match .num{color:var(--match)}.stat.v-mismatch .num{color:var(--mismatch)}
.stat.v-missing .num{color:var(--missing)}.stat.v-na .num{color:var(--na)}
.stat .lbl{display:block;font-size:11px;color:var(--muted);white-space:nowrap}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 18px}
.filters button{font:inherit;font-size:13px;padding:6px 13px;border-radius:99px;
border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
.filters button[aria-pressed=true]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.domain{margin:0 0 30px;border:1px solid var(--line);border-radius:12px;
background:var(--card);padding:16px}
.domain h3{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:12px}
.cnt{font-size:12px;color:var(--muted);font-weight:400;margin-left:auto}
.draft{font-size:11px;color:var(--missing);background:var(--missing-bg);
padding:2px 8px;border-radius:99px}
.rule{border-top:1px solid var(--line);padding:11px 0}
.rule summary{cursor:pointer;display:flex;gap:12px;justify-content:space-between;
align-items:flex-start;flex-wrap:wrap;list-style:none}
.rule summary::-webkit-details-marker{display:none}
.rule summary::before{content:"▸";color:var(--muted);flex:none;margin-right:-6px}
.rule[open] summary::before{content:"▾"}
.rsum{flex:1 1 320px;min-width:0}
.rid{display:inline-block;background:var(--na-bg);padding:1px 7px;border-radius:5px;margin-right:8px}
.rtext{color:var(--fg)}
.lowconf{font-size:11px;color:var(--missing);border:1px solid var(--missing);
padding:0 6px;border-radius:99px;margin-left:6px;white-space:nowrap}
.pills{display:flex;gap:6px;flex-wrap:wrap;flex:none}
.pill{font-size:11px;padding:3px 9px;border-radius:99px;white-space:nowrap;
background:var(--na-bg);color:var(--na)}
.pill.v-match{background:var(--match-bg);color:var(--match)}
.pill.v-mismatch{background:var(--mismatch-bg);color:var(--mismatch)}
.pill.v-missing{background:var(--missing-bg);color:var(--missing)}
.pdetails{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
margin:12px 0 4px;padding-left:18px}
.pdetail{border:1px solid var(--line);border-radius:9px;padding:11px 13px;background:var(--bg)}
.phead{display:flex;align-items:center;gap:7px;font-weight:600;font-size:13px;margin-bottom:6px}
.dot{width:9px;height:9px;border-radius:99px;flex:none;background:var(--na)}
.dot.v-match{background:var(--match)}.dot.v-mismatch{background:var(--mismatch)}
.dot.v-missing{background:var(--missing)}
.conf{font-size:10px;color:var(--muted);border:1px solid var(--line);
padding:0 5px;border-radius:4px;margin-left:auto;font-weight:400}
.conf.c-low{color:var(--missing);border-color:var(--missing)}
.note{margin:0 0 6px;font-size:13px;color:var(--fg)}
.note.muted{color:var(--muted)}
.ev{margin:0;padding-left:17px;font-size:12px;color:var(--muted)}
.ev li{overflow-wrap:anywhere;margin:2px 0}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:10px 0 0}
.legend span{display:flex;align-items:center;gap:5px}
footer{margin-top:50px;padding-top:18px;border-top:1px solid var(--line);
color:var(--muted);font-size:12px}
@media print{.filters{display:none}.rule{break-inside:avoid}details{open:true}}
"""

JS = """
document.querySelectorAll('.filters button').forEach(function(btn){
  btn.addEventListener('click', function(){
    var f = btn.dataset.filter;
    document.querySelectorAll('.filters button').forEach(function(b){
      b.setAttribute('aria-pressed', String(b === btn));
    });
    document.querySelectorAll('.rule').forEach(function(r){
      r.style.display = (f === 'all' || r.classList.contains('has-' + f)) ? '' : 'none';
    });
    document.querySelectorAll('.domain').forEach(function(d){
      var any = Array.prototype.some.call(d.querySelectorAll('.rule'), function(r){
        return r.style.display !== 'none';
      });
      d.style.display = any ? '' : 'none';
    });
  });
});
"""


def render(data: dict) -> str:
    per_platform = tally(data)
    started = data["started_at"]
    total_rules = sum(len(d["rules"]) for d in data["domains"])
    overall = Counter()
    for c in per_platform.values():
        overall.update(c)

    cards = "".join(
        platform_card(p, label, per_platform[p]) for p, label in PLATFORMS
    )
    subs = data.get("submodules") or {}
    sub_line = (
        " · ".join(f"{k}: <code>{esc(v)}</code>" for k, v in subs.items())
        if subs else "서브모듈 정보 없음"
    )
    domains = "".join(domain_section(d) for d in data["domains"])
    legend = "".join(
        f'<span><i class="dot v-{v}" style="display:inline-block"></i>{VERDICT_LABEL[v]}</span>'
        for v in VERDICTS
    )

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>정책↔구현 대조 보고서 {esc(started)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>정책 ↔ 구현 대조 보고서</h1>
  <p class="meta">분석 시작 <code>{esc(started.replace('T', ' '))}</code>
     · 대상 규칙 <strong>{total_rules}</strong>개 · 도메인 {len(data['domains'])}개
     · 판정 {sum(overall.values())}건</p>
  <p class="meta">{sub_line}</p>

  <h2>개요</h2>
  <div class="cards">{cards}</div>
  <div class="legend">{legend}</div>

  <h2>상세</h2>
  <div class="filters">
    <button data-filter="all" aria-pressed="true">전체</button>
    <button data-filter="mismatch" aria-pressed="false">잘못 구현만</button>
    <button data-filter="missing" aria-pressed="false">미구현만</button>
    <button data-filter="match" aria-pressed="false">맞게 구현만</button>
  </div>
  {domains}

  <footer>
    각 규칙 줄을 클릭하면 플랫폼별 근거와 메모가 펼쳐집니다.
    비율은 '대상 아님'을 제외한 건수 기준입니다.
    정책 근거는 <code>wiki/domains/</code>이며, 구현 코드는 근거가 아닙니다.
  </footer>
</div>
<script>{JS}</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="정책↔구현 대조 HTML 보고서 생성")
    ap.add_argument("--findings", required=True, help="findings JSON 경로")
    ap.add_argument("--out-dir", default="reports", help="보고서 출력 디렉터리")
    args = ap.parse_args()

    src = Path(args.findings)
    if not src.exists():
        fail(f"findings 파일이 없다: {src}")
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"findings JSON 파싱 실패: {e}")

    validate(data)

    stamp = datetime.strptime(data["started_at"], "%Y-%m-%dT%H:%M:%S")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"policy-audit-{stamp:%Y%m%d-%H%M%S}.html"
    out.write_text(render(data), encoding="utf-8")

    per_platform = tally(data)
    print(str(out))
    for p, label in PLATFORMS:
        c = per_platform[p]
        print(
            f"  {label:<8} 맞게 {c.get('match',0)} / "
            f"잘못 {c.get('mismatch',0)} / 미구현 {c.get('missing',0)} / 대상아님 {c.get('na',0)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
