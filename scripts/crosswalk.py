#!/usr/bin/env python3
"""kr-compliance-crosswalk 데이터 검증 및 기준 간 대응 계산.

사용법:
    python scripts/crosswalk.py validate
    python scripts/crosswalk.py derive --from isms-p --to iso27001-2022

외부 패키지 없이 Python 3.9+ 표준 라이브러리만 사용한다.
규칙 정의는 docs/schema.md 참고.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SCHEMA = {
    "frameworks.csv": ["framework_id", "name", "version", "issuer", "source_url", "note"],
    "controls": ["control_id", "domain", "title_ko", "title_en"],
    "common_controls.csv": ["cc_id", "name_ko", "name_en", "description", "category"],
    "mappings.csv": ["framework_id", "control_id", "cc_id", "relation", "gap_note",
                     "rationale", "status", "reviewed_at"],
    "evidence.csv": ["evidence_id", "cc_id", "name", "description", "frequency"],
}
RELATIONS = {"equal", "within", "contains", "related"}
STATUSES = {"draft", "reviewed"}
CC_ID = re.compile(r"^CC-[A-Z]{2}-\d{2,}$")
EV_ID = re.compile(r"^EV-\d{3,}$")

# X => C : X 를 충족하면 공통 통제 C 도 충족
IMPLIES_CC = {"equal", "contains"}
# C => Y : 공통 통제 C 를 충족하면 Y 도 충족
CC_IMPLIES = {"equal", "within"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")


def read_csv(path: Path, expected: list[str], rep: Report) -> list[dict]:
    rel = path.relative_to(ROOT)
    if not path.exists():
        rep.err(str(rel), "파일이 없음")
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected:
            rep.err(str(rel), f"헤더 불일치. 기대값 {expected}, 실제 {reader.fieldnames}")
            return []
        rows = []
        for i, row in enumerate(reader, start=2):
            row = {k: (v or "").strip() for k, v in row.items() if k is not None}
            row["_where"] = f"{rel}:{i}"
            rows.append(row)
        return rows


def require(row: dict, cols: list[str], rep: Report) -> None:
    for c in cols:
        if not row.get(c):
            rep.err(row["_where"], f"'{c}' 값이 비어 있음")


def load(rep: Report):
    fws = read_csv(DATA / "frameworks.csv", SCHEMA["frameworks.csv"], rep)
    fw_ids = set()
    for r in fws:
        require(r, ["framework_id", "name", "version", "issuer"], rep)
        if r["framework_id"] in fw_ids:
            rep.err(r["_where"], f"framework_id 중복: {r['framework_id']}")
        fw_ids.add(r["framework_id"])

    controls: dict[str, dict[str, dict]] = {}
    for fid in sorted(fw_ids):
        rows = read_csv(DATA / "controls" / f"{fid}.csv", SCHEMA["controls"], rep)
        controls[fid] = {}
        for r in rows:
            require(r, ["control_id"], rep)
            if not (r["title_ko"] or r["title_en"]):
                rep.err(r["_where"], "title_ko, title_en 중 하나는 필요")
            if r["control_id"] in controls[fid]:
                rep.err(r["_where"], f"control_id 중복: {r['control_id']}")
            controls[fid][r["control_id"]] = r

    ccs = {}
    for r in read_csv(DATA / "common_controls.csv", SCHEMA["common_controls.csv"], rep):
        require(r, ["cc_id", "name_ko", "description", "category"], rep)
        if r["cc_id"] and not CC_ID.match(r["cc_id"]):
            rep.err(r["_where"], f"cc_id 형식 오류(CC-XX-00): {r['cc_id']}")
        elif r["cc_id"] and r["cc_id"].split("-")[1] != r["category"]:
            rep.err(r["_where"], f"cc_id 영역과 category 불일치: {r['cc_id']} / {r['category']}")
        if r["cc_id"] in ccs:
            rep.err(r["_where"], f"cc_id 중복: {r['cc_id']}")
        ccs[r["cc_id"]] = r

    maps = read_csv(DATA / "mappings.csv", SCHEMA["mappings.csv"], rep)
    seen = set()
    for r in maps:
        require(r, ["framework_id", "control_id", "cc_id", "relation", "rationale", "status"], rep)
        if r["framework_id"] not in fw_ids:
            rep.err(r["_where"], f"없는 framework_id: {r['framework_id']}")
        elif r["control_id"] not in controls.get(r["framework_id"], {}):
            rep.err(r["_where"], f"{r['framework_id']}에 없는 control_id: {r['control_id']}")
        if r["cc_id"] not in ccs:
            rep.err(r["_where"], f"없는 cc_id: {r['cc_id']}")
        if r["relation"] not in RELATIONS:
            rep.err(r["_where"], f"relation 허용값 아님: {r['relation']} (허용: {sorted(RELATIONS)})")
        if r["relation"] == "contains" and not r["gap_note"]:
            rep.err(r["_where"], "relation이 contains이면 gap_note 필수")
        if r["status"] not in STATUSES:
            rep.err(r["_where"], f"status 허용값 아님: {r['status']}")
        if r["status"] == "reviewed":
            try:
                date.fromisoformat(r["reviewed_at"])
            except ValueError:
                rep.err(r["_where"], "status가 reviewed이면 reviewed_at(YYYY-MM-DD) 필수")
        key = (r["framework_id"], r["control_id"], r["cc_id"])
        if key in seen:
            rep.err(r["_where"], f"같은 대응 중복: {key}")
        seen.add(key)

    for r in read_csv(DATA / "evidence.csv", SCHEMA["evidence.csv"], rep):
        require(r, ["evidence_id", "cc_id", "name"], rep)
        if r["evidence_id"] and not EV_ID.match(r["evidence_id"]):
            rep.err(r["_where"], f"evidence_id 형식 오류(EV-000): {r['evidence_id']}")
        if r["cc_id"] not in ccs:
            rep.err(r["_where"], f"없는 cc_id: {r['cc_id']}")

    return fw_ids, controls, ccs, maps


def cmd_validate(_: argparse.Namespace) -> int:
    rep = Report()
    fw_ids, controls, ccs, maps = load(rep)
    if rep.errors:
        print(f"검증 실패: 오류 {len(rep.errors)}건")
        for e in rep.errors:
            print(f"  - {e}")
        return 1
    n_ctrl = sum(len(v) for v in controls.values())
    mapped = {(m["framework_id"], m["control_id"]) for m in maps}
    print("검증 통과")
    print(f"  기준 {len(fw_ids)}개, 항목 {n_ctrl}개, 공통 통제 {len(ccs)}개, 대응 {len(maps)}건")
    for fid in sorted(fw_ids):
        total = len(controls[fid])
        done = sum(1 for c in controls[fid] if (fid, c) in mapped)
        pct = (done / total * 100) if total else 0
        print(f"  {fid}: {done}/{total} 항목 대응 ({pct:.0f}%)")
    return 0


def cmd_derive(args: argparse.Namespace) -> int:
    rep = Report()
    fw_ids, _, _, maps = load(rep)
    if rep.errors:
        print("데이터 오류가 있어 계산할 수 없습니다. 먼저 validate를 실행하세요.")
        return 1
    for fid in (args.src, args.dst):
        if fid not in fw_ids:
            print(f"없는 framework_id: {fid} (사용 가능: {sorted(fw_ids)})")
            return 1

    by_cc: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for m in maps:
        by_cc[m["cc_id"]][m["framework_id"]].append(m)

    rows = []
    for cc, fw in sorted(by_cc.items()):
        for x in fw.get(args.src, []):
            for y in fw.get(args.dst, []):
                fwd = x["relation"] in IMPLIES_CC and y["relation"] in CC_IMPLIES
                bwd = y["relation"] in IMPLIES_CC and x["relation"] in CC_IMPLIES
                draft = "draft" in (x["status"], y["status"])
                if fwd and bwd:
                    rows.append((x["control_id"], "<->", y["control_id"], cc, "상호 충족", draft))
                elif fwd:
                    rows.append((x["control_id"], "->", y["control_id"], cc,
                                 f"{x['control_id']}을 충족하면 {y['control_id']}도 충족 (단방향)", draft))
                elif bwd:
                    rows.append((y["control_id"], "->", x["control_id"], cc,
                                 f"{y['control_id']}을 충족하면 {x['control_id']}도 충족 (단방향)", draft))
                else:
                    rows.append((x["control_id"], "~", y["control_id"], cc, "참고 관계 (충족 관계 없음)", draft))

    if not rows:
        print(f"{args.src}와 {args.dst} 사이에 공통 통제로 연결된 항목이 없습니다.")
        return 0
    print(f"{'from':<10}{'':4}{'to':<10}{'via':<11}result")
    for a, arrow, b, cc, msg, draft in rows:
        flag = "  [draft]" if draft else ""
        print(f"{a:<10}{arrow:<4}{b:<10}{cc:<11}{msg}{flag}")
    print("\n'draft'는 검토 전 대응입니다. 최종 판단은 기준 원문으로 확인하세요.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="kr-compliance-crosswalk 도구")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="데이터 검증").set_defaults(func=cmd_validate)
    d = sub.add_parser("derive", help="두 기준 간 대응 계산")
    d.add_argument("--from", dest="src", required=True, help="기준 A framework_id")
    d.add_argument("--to", dest="dst", required=True, help="기준 B framework_id")
    d.set_defaults(func=cmd_derive)
    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
