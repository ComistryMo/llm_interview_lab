"""Offline 48-case CLI compilation/replay. CLI never connects or reads keyring.

Usage: python scripts/evaluate_interviewer_expertise.py --output <new-directory>
Optional --responses reads explicitly supplied sNNN.txt model output artifacts;
it validates them with each protocol's OWN parser. It does not score semantic
quality or infer it from scripted outputs. --baseline-source reads an isolated
public-source export of the recorded baseline, never the current v2 builder.
The separate transmit_authorized_case API accepts an existing adapter and an
explicit per-request consent digest; it is non-network unless execute=True.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
BASELINE_SHA = "b954c71d6a7029010fc247cbf7eef6c880a102f1"


async def transmit_authorized_case(preview, instruction, *, descriptor, provider=None,
                                  codex_backend=None, thread_id=None, output_schema=None,
                                  execute=False, consent_sha256=""):
    """Explicit eval transport using an already configured application adapter.

    No credential lookup. The caller owns the adapter/event pump (not a running
    desktop interview's pump). Default is an inspectable, non-network request.
    Consent binds exact payload and model/provider/effort, separately per case.
    """
    from time import perf_counter
    from llm_interview_lab.ai.interview_context_budget import enforce_wire_budget
    if provider is not None:
        actual = {key: getattr(provider.config, key) for key in ("provider_id", "model", "reasoning_effort", "base_url")}
        if descriptor != actual:
            raise ValueError("评测参数必须与传入的现有连接配置一致。")
    messages = [{"role": "system", "content": preview.selected_text}, {"role": "user", "content": instruction}]
    prompt = preview.selected_text + "\n\n## Frozen scorecard contract\n" + instruction
    wire = {"prompt": prompt, "output_schema": output_schema} if codex_backend else messages
    encoded = json.dumps({"descriptor": descriptor, "wire": wire}, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    result = {"consent_sha256": digest, "request": wire, "parameters": descriptor,
              "size": enforce_wire_budget(json.dumps(wire, ensure_ascii=False)), "network_calls": 0,
              "semantic_quality": "UNRUN"}
    if not execute:
        return result
    if not consent_sha256 or consent_sha256 != digest:
        raise ValueError("评测发送范围或模型设置未获确认；未发起请求。")
    if (provider is None) == (codex_backend is None):
        raise ValueError("显式选择一个现有传输适配器。")
    start, first, pieces = perf_counter(), None, []
    if provider is not None:
        async for event in provider.stream_chat(messages):
            if event.kind == "error":
                raise ValueError("评测传输失败；保留原始失败，不自动重试。")
            if event.kind == "delta" and event.text:
                first = first or perf_counter()
                pieces.append(event.text)
    else:
        if not thread_id:
            raise ValueError("Codex 评测必须由调用方显式提供其独占的现有线程，不接管应用活动线程。")
        turn = await codex_backend.start_turn(thread_id, prompt, model=descriptor.get("model"),
            effort=descriptor.get("reasoning_effort"), output_schema=output_schema)
        turn_id = turn["turn"]["id"]
        completed = False
        async for event in codex_backend.events():
            nested = event.params.get("turn", {})
            if (event.params.get("turnId") or nested.get("id")) != turn_id:
                continue
            if event.method == "item/agentMessage/delta":
                first = first or perf_counter()
                pieces.append(event.params.get("delta", ""))
            if event.method == "turn/completed":
                if nested.get("status", event.params.get("status")) != "completed":
                    raise ValueError("本次显式评测未成功完成；不会自动重试。")
                completed = True
                break
            if event.method in ("turn/failed", "turn/aborted", "turn/cancelled", "error"):
                raise ValueError("本次显式评测失败或取消；不会自动重试。")
        if not completed:
            raise ValueError("Codex 评测未收到完成事件，不记录为成功。")
    result.update(network_calls=1, raw_response="".join(pieces),
                  first_text_seconds=None if first is None else first-start, completed_seconds=perf_counter()-start)
    return result


def preserve_synthetic_artifacts(source, destination):
    """Explicit 48-case file allowlist, not a recursive TEMP/Profile export."""
    destination.mkdir(parents=True, exist_ok=False)
    names = ["summary.json"] + [f"s{i:03d}.{suffix}" for i in range(1, 49)
        for suffix in ("request.json", "review-only.json", "response.txt")]
    manifest = {"synthetic_only": True, "baseline_sha": BASELINE_SHA, "files": {}}
    for name in names:
        path = source / name
        if path.is_file():
            shutil.copyfile(path, destination / name)
            manifest["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def isolated_public_repo(source, destination):
    destination.mkdir(parents=True)
    for name in ("pyproject.toml", ".gitignore", "AGENTS.md"):
        shutil.copy2(source / name, destination / name)
    for name in ("curriculum", "coach", "workspace/schema", "workspace/templates"):
        shutil.copytree(source / name, destination / name)
    (destination / "workspace/profiles").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=destination, check=True, capture_output=True)


def contract_of(preview):
    return json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))


def compile_input(service, profile, value, *, legacy=False):
    """Only model-input data enters the application; no evaluator labels."""
    from llm_interview_lab.ai.context_builder import build_role_interview_context_preview
    def preview(iid, answer):
        return build_role_interview_context_preview(service.repo_root, profile, iid,
            candidate_answer=answer, include_materials=False, catalog=service.catalog, role_catalog=service.roles)
    first = value["history"][0]
    kwargs = {} if legacy else {"interaction_version": 3}
    session = service.create_dynamic_interview(profile, role_id=value["role_id"], difficulty=value["difficulty"],
        duration_minutes=60, ai_mode="provider", context_sha256="a" * 64,
        initial_question={"kind": "oral", "title": "自我介绍", "prompt": first["question"], "source_kind": "process_opening"}, **kwargs)
    iid = session["interview_id"]
    service.start_interview(profile, iid)
    skill = next(iter(service.roles.resolve_role(value["role_id"]).skill_weights))
    for index, previous in enumerate(value["history"]):
        qid = f"q-{index + 1:03d}"
        service.answer_interview(profile, iid, qid, previous["answer"])
        compiled = preview(iid, previous["answer"])
        next_prompt = value["history"][index + 1]["question"] if index + 1 < len(value["history"]) else value["question"]
        decision = {"follow_up": next_prompt, "next_stage": "experience", "coding_problem_id": "", "next_skill_ids": [skill]}
        if legacy:
            decision["coverage"] = {"experience": "合成工作", "topic": "", "angle": "ownership", "sufficient": False, "evidence": previous["answer"][:100]}
            extra = {}
        else:
            c = contract_of(compiled)
            quote = {"question_id": qid, "quote": previous["answer"][:100]}
            ref = "new:described-work" if index == 0 else "claim-0001"
            decision.update(state_update={"experiences": [], "claims": [{"ref": ref, "experience_ref": "",
                "topic_id": skill, "angle": "ownership", "criterion": "contribution",
                "statement": "候选人描述的合成工作待核实", "status": "partial", "assessment_note": "只记录已描述范围，不预判技术正确性。", "evidence": quote}],
                "contradictions": [], "closures": []},
                probe={"claim_ref": ref, "topic_id": skill, "criterion": "contribution", "method_id": "core",
                    "knowledge_ids": [], "action": "invite" if index == 0 else "inspect"},
                transition_reason="introduction_complete" if index == 0 else "continue")
            extra = {"request_contract": c}
        service.advance_dynamic_interview(profile, iid, qid, decision,
            context_sha256=hashlib.sha256(compiled.selected_text.encode()).hexdigest(), **extra)
    qid = f"q-{len(value['history']) + 1:03d}"
    service.answer_interview(profile, iid, qid, value["answer"])
    return iid, preview(iid, value["answer"])


def evaluate(source, output, cases, *, legacy=False, responses=None):
    from llm_interview_lab.application import ApplicationService
    from llm_interview_lab.workspace import init_profile
    from llm_interview_lab.interview_flow import next_question_instruction, decode_next_question
    runtime = output / "synthetic-runtime"
    isolated_public_repo(source, runtime)
    service = ApplicationService(runtime)
    results = []
    for case in cases:
        profile = "eval-" + case["id"]
        init_profile(runtime, profile, display_name="合成候选人")
        iid, preview = compile_input(service, profile, case["input"], legacy=legacy)
        contract = contract_of(preview)
        version = 2 if legacy else 3
        instruction = next_question_instruction() if legacy else next_question_instruction(3)
        business = {"system": preview.selected_text, "instruction": instruction}
        # The evaluator sidecar is never concatenated to business content.
        payload = json.dumps(business, ensure_ascii=False)
        assert not any(marker in payload for marker in ('"answer_type"', '"expected_gap"', '"accept_direction"', '"technical_basis"'))
        result = {"id": case["id"], "protocol": version, "network_calls": 0,
            "semantic_quality": "UNRUN", "characters": len(payload), "utf8_bytes": len(payload.encode()), "tokens": None,
            "input_sha256": hashlib.sha256(json.dumps(case["input"], sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "compiled_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "methods": contract.get("methods", []), "references": contract.get("expert_references", []),
            "sent_answer_sources": contract.get("sent_answer_sources", []), "local_validation": "passed"}
        if not legacy:
            from llm_interview_lab.desktop.controller import _dynamic_response_schema
            from llm_interview_lab.ai.interview_context_budget import enforce_wire_budget
            schema = _dynamic_response_schema(preview, set(), set())
            provider = [{"role": "system", "content": preview.selected_text}, {"role": "user", "content": instruction}]
            codex = {"prompt": preview.selected_text + "\n\n## Frozen scorecard contract\n" + instruction, "output_schema": schema}
            result["provider_wire"] = enforce_wire_budget(json.dumps(provider, ensure_ascii=False))
            result["codex_wire"] = enforce_wire_budget(json.dumps(codex, ensure_ascii=False))
            assert set(contract["loaded_method_ids"]) == set(schema["properties"]["probe"]["properties"]["method_id"]["enum"]) - {"core"}
            assert len(contract["methods"]) <= 2
            assert case["evaluation"]["topic_id"] in {r["topic_id"] for r in contract["expert_references"]}, "current topic missing from retrieved references"
        (output / f"{case['id']}.request.json").write_text(json.dumps(business, ensure_ascii=False, indent=2), encoding="utf-8")
        (output / f"{case['id']}.review-only.json").write_text(json.dumps(case["evaluation"], ensure_ascii=False, indent=2), encoding="utf-8")
        if responses:
            path = responses / f"{case['id']}.txt"
            if path.exists():
                raw = path.read_text(encoding="utf-8")
                (output / f"{case['id']}.response.txt").write_text(raw, encoding="utf-8")
                try:
                    decision = decode_next_question(raw) if legacy else decode_next_question(raw, version=3)
                    qid = f"q-{len(case['input']['history']) + 1:03d}"
                    extra = {} if legacy else {"request_contract": contract}
                    service.advance_dynamic_interview(profile, iid, qid, decision,
                        context_sha256=hashlib.sha256(preview.selected_text.encode()).hexdigest(), **extra)
                    result["replay_validation"] = "passed"
                except (ValueError, RuntimeError) as error:
                    result["replay_validation"] = "failed"
                    result["error_type"] = type(error).__name__
        results.append(result)
        print(f"{case['id']}: compiled protocol {version}", flush=True)
    summary = {"baseline_sha": BASELINE_SHA, "source": str(source), "network_calls": 0,
        "semantic_quality": "UNRUN", "real_latency": "UNRUN", "expert_blind_review": "UNRUN", "cases": results}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--baseline-source", type=Path)
    parser.add_argument("--export-baseline", action="store_true", help="从原始提交只导出公开源码，不 checkout 当前工作树")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    output = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix="interviewer-eval-")).resolve()
    if args.output:
        output.mkdir(parents=True, exist_ok=False)
    source = (args.baseline_source or REPO).resolve()
    if args.export_baseline:
        source = output / "baseline-source"
        source.mkdir()
        archive = output / "baseline-public.zip"
        subprocess.run(["git", "archive", "--format=zip", "-o", str(archive), BASELINE_SHA,
            "src", "curriculum", "coach", "workspace/schema", "workspace/templates", "pyproject.toml", ".gitignore", "AGENTS.md"],
            cwd=REPO, check=True)
        with zipfile.ZipFile(archive) as content:
            content.extractall(source)
        manifest = {"commit": BASELINE_SHA, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "files": {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source.rglob("*") if p.is_file()}}
        (source / "baseline-source.json").write_text(json.dumps(manifest), encoding="utf-8")
        for p in source.rglob("*"):
            if p.is_file():
                p.chmod(0o444)
    legacy = bool(args.baseline_source or args.export_baseline)
    if legacy:
        manifest = json.loads((source / "baseline-source.json").read_text(encoding="utf-8"))
        assert manifest["commit"] == BASELINE_SHA
        for relative, digest in manifest["files"].items():
            path = (source / relative).resolve()
            assert path.is_relative_to(source) and hashlib.sha256(path.read_bytes()).hexdigest() == digest
        sys.dont_write_bytecode = True
    # Import old source in a fresh process with this path first, not version=2
    # on today's builder. Caller supplies only the explicitly exported commit.
    sys.path.insert(0, str(source / "src"))
    dataset = json.loads((REPO / "tests/fixtures/interviewer-expertise-scenarios.json").read_text(encoding="utf-8"))
    from jsonschema import validate
    validate(dataset, json.loads((REPO / "tests/fixtures/interviewer-expertise-scenarios.schema.json").read_text(encoding="utf-8")))
    evaluate(source, output, dataset["cases"][:args.limit], legacy=legacy, responses=args.responses)
    print(output)


if __name__ == "__main__":
    main()
