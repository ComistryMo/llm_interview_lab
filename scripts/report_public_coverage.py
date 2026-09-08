"""Generate a public Catalog/knowledge snapshot; never open a Profile."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform

from llm_interview_lab import __version__
from llm_interview_lab.application import ApplicationService


def coverage(root: Path) -> dict:
    service = ApplicationService(root)
    knowledge = service.knowledge_catalog()
    rows = []
    for pid in service.catalog.order:
        problem = service.catalog.get(pid)
        framework = problem.raw.get("interface", {}).get("framework", "python")
        environment = service._problem_environment_available(problem)
        retention = {stage: "retention" in problem.raw and problem.retention_variant(root, stage) is not None for stage in ("d2", "d7")}
        rows.append({"id": pid, "kind": problem.kind, "status": problem.status,
            "validation": problem.validation_level if problem.ready else "planned", "recommendable": problem.recommendable,
            "framework": framework, "environment_available": environment,
            "coding_runnable": problem.recommendable and problem.kind in {"coding", "debugging"} and environment,
            "retention_ready": problem.recommendable and all(retention.values()),
            **retention, "tracks": problem.raw["tracks"], "prerequisites": list(problem.prerequisites),
            "asset_root": problem.problem_dir.relative_to(root).as_posix() if problem.problem_dir else None})
    def counts(items):
        return {"total": len(items), "status": dict(Counter(row["status"] for row in items)),
                "validation": dict(Counter(row["validation"] for row in items)),
                **{key: sum(row[key] for row in items) for key in ("recommendable", "coding_runnable", "retention_ready", "d2", "d7")}}
    hashes = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for base in ("curriculum", "coach", "workspace/schema", "workspace/templates")
              for path in sorted((root / base).rglob("*"))
              if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    return {"schema_version": 1, "source_version": __version__, "environment": {"system": platform.system(), "machine": platform.machine(), "python": platform.python_version()},
            "notes": "Public metadata only; runtime eligibility is not proof of learner mastery or successful execution. Tracks overlap. Pending author assets are excluded.",
            "totals": counts(rows), "tracks": {track: counts([row for row in rows if track in row["tracks"]]) for track in service.catalog.tracks},
            "knowledge": {"cards": len(knowledge.cards), "sources": len(knowledge.sources), "kinds": dict(Counter(card.kind for card in knowledge.cards.values()))},
            "problems": rows, "public_assets_sha256": hashes}


def markdown(report: dict) -> str:
    totals = report["totals"]
    lines = ["# 候选版公共内容快照", "", f"源码版本：`{report['source_version']}`。由 `scripts/report_public_coverage.py` 生成，不是第二份题库元数据。", "",
        f"Catalog {totals['total']} 个节点；状态 {totals['status']}；验证级别 {totals['validation']}。",
        f"可推荐 {totals['recommendable']}；此环境具备依赖的已验证代码题 {totals['coding_runnable']}；D+2/D+7 均验证的节点 {totals['retention_ready']}。",
        f"知识卡 {report['knowledge']['cards']}，来源 {report['knowledge']['sources']}。", "",
        "可运行资格不等于本轮逐题执行通过，也不等于解锁或 Mastery。未完成前置仍不可从 Practice 启动；面试候选继续使用自己的确定性规则。打包是否含 PyTorch/NumPy 需用包内环境重新检查，不能照抄开发环境数量。", "",
        "| Track（交叉归属不相加） | 全部 | planned | 已验证可推荐 | 本环境代码可运行 | D+2/D+7 齐全 |",
        "|---|---:|---:|---:|---:|---:|"]
    for track, row in report["tracks"].items():
        lines.append(f"| {track} | {row['total']} | {row['status'].get('planned', 0)} | {row['recommendable']} | {row['coding_runnable']} | {row['retention_ready']} |")
    lines += ["", "## 候选闭环缺口", "", "当前主要缺口是部分已验证训练题尚无 D+2/D+7 资产，而不是继续堆叠同主题主问题。新变式须经 Oracle/property 验证及准入检查后再登记；待审资产不得算进上表。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    report = coverage(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"totals": report["totals"], "knowledge": report["knowledge"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
