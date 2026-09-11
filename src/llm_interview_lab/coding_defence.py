"""Coding subturns: frozen sources, parent scoring, existing session clock."""
import hashlib
import json

MIN_REMAINING_SECONDS = 60  # Leave a meaningful reading/answer window; never extend the session.
MAX_QUESTIONS = 2


def enabled(session):
    return session.get("interaction_version") == 3 and session.get("coding_defence_version") == 1


def active(session):
    return enabled(session) and bool(session.get("coding_defence"))


def sources(session, answers):
    """Only the canonical locked snapshot and saved child answers, never editor files."""
    if not active(session):
        return []
    d = session["coding_defence"]
    parent = d["parent_question_id"]
    if parent not in answers:
        raise ValueError("答辩缺少父题锁定快照；不会重新创建提交。")
    snapshot = json.loads(answers[parent][0])
    if (not isinstance(snapshot, dict) or not isinstance(snapshot.get("code"), str)
            or snapshot.get("submission_sha256") != d["submission_sha256"]
            or any(not isinstance(snapshot.get(key), dict) or "status" not in snapshot[key]
                   for key in ("self_run", "public_tests"))):
        raise ValueError("代码快照或执行来源结构损坏；请恢复该场次备份。")
    code = snapshot["code"]
    if hashlib.sha256(code.encode("utf-8")).hexdigest() != d["submission_sha256"]:
        raise ValueError("锁定代码校验失败；请恢复该场次备份，不会重新锁定。")
    result = [{"source_id": "code:" + parent, "kind": "locked_code", "question_id": parent,
               "sha256": d["submission_sha256"], "text": code}]
    for key, kind in (("self_run", "self_run"), ("public_tests", "public_tests")):
        value = snapshot[key]
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        result.append({"source_id": ("run:" if key == "self_run" else "test:") + parent,
            "kind": kind, "question_id": parent, "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "submission_sha256": value.get("submission_sha256"),
            "matches_locked_code": value.get("submission_sha256") == d["submission_sha256"], "text": text})
    for qid in d["question_ids"]:
        if qid in answers:
            text, digest = answers[qid]
            result.append({"source_id": qid, "kind": "oral_answer", "question_id": qid,
                           "sha256": digest, "text": text})
    return result


def validate(session, answers):
    if "coding_defence_version" in session and not enabled(session):
        raise ValueError("不支持的代码答辩契约版本。")
    if not session.get("coding_defence"):
        return
    d = session["coding_defence"]
    questions = {q["question_id"]: q for q in session["questions"]}
    parent = questions.get(d["parent_question_id"], {})
    if (not enabled(session) or parent.get("kind") != "coding" or
            parent.get("source", {}).get("sha256") != d["task_sha256"] or
            len(d["question_ids"]) > MAX_QUESTIONS or len(set(d["question_ids"])) != len(d["question_ids"]) or
            d["status"] not in ("pending", "answering", "closed")):
        raise ValueError("代码答辩关联损坏；不会自动重建。")
    for qid in d["question_ids"]:
        q = questions.get(qid, {})
        if q.get("parent_coding_question_id") != parent["question_id"] or q.get("kind") != "oral" or q.get("stage") != "coding":
            raise ValueError("代码答辩子题关联损坏。")
    linked = {qid for qid, q in questions.items() if q.get("parent_coding_question_id")}
    if linked != set(d["question_ids"]) or (d["status"] == "closed") != bool(d["close_reason"]):
        raise ValueError("代码答辩数量或关闭原因不一致。")
    sources(session, answers)


def close(session, reason, remaining):
    d = session["coding_defence"]
    if d["status"] != "closed":
        d.update(status="closed", close_reason=reason, closed_remaining_seconds=remaining)


def should_close(session, remaining):
    d = session["coding_defence"]
    if d["status"] == "closed":
        return d["close_reason"]
    if remaining < MIN_REMAINING_SECONDS:
        return "time_deferred"
    if len(d["question_ids"]) >= MAX_QUESTIONS and d["question_ids"][-1] in session["answers"]:
        return "question_limit"
    return ""


def advance(repo_root, profile_id, session, question_id, decision, contract, context_sha, now):
    from . import role_interviews as ri, interviewer_state as state
    d = session["coding_defence"]
    remaining = ri._remaining_seconds(session, now)
    if d["status"] == "closed" or remaining <= 0:
        raise ValueError("本场答辩已关闭或到时；未接纳晚到问题。")
    if decision["next_stage"] not in ("coding", "finish") or decision["coding_problem_id"]:
        raise ValueError("答辩不能回到原理或另选代码题。")
    first = not d["question_ids"]
    if first and decision["next_stage"] != "coding":
        raise ValueError("首道答辩须围绕已锁定代码；失败不能伪装成跳过。")
    answers = {qid: (ri._locked_answer_text(repo_root, profile_id, session["interview_id"], qid, rec), rec["sha256"])
               for qid, rec in session["answers"].items()}
    registry = sources(session, answers)
    answers.update({s["source_id"]: (s["text"], s["sha256"]) for s in registry})
    merged = state.merge_decision(session, decision, contract["request_basis"], answers,
        allowed_topics={s["id"] for s in contract["role_skills"]} | set(contract["loaded_knowledge_ids"]),
        allowed_knowledge=contract["loaded_knowledge_ids"], allowed_methods=contract["loaded_method_ids"],
        source_scope=contract["sent_answer_sources"], allowed_claims=contract["allowed_probe_claim_ids"],
        defence=True)
    probe = decision["probe"]
    if decision["next_stage"] == "coding":
        if len(d["question_ids"]) >= MAX_QUESTIONS or remaining < MIN_REMAINING_SECONDS:
            raise ValueError("剩余时间或答辩次数不允许新增问题；请保留回答并结束本场。")
        if probe["method_id"] != "code-defense-failure-analysis":
            raise ValueError("代码答辩须使用本轮加载的代码核查方法。")
        claim = merged["claims"].get(merged["probes"][-1]["claim_id"], {})
        if first and not any(e["question_id"] == "code:" + d["parent_question_id"] for e in claim.get("evidence", [])):
            raise ValueError("首问必须锚定锁定代码的连续原文。")
        if not first and claim.get("criterion_status") not in ("partial", "disputed", "unassessed", "explicit_unknown", "not_owned"):
            raise ValueError("第二问需要具体且尚未解决的代码缺口。")
        parent = next(q for q in session["questions"] if q["question_id"] == d["parent_question_id"])
        qid = f"q-{len(session['questions']) + 1:03d}"
        question = ri._generated_non_coding_question(
            {"kind": "oral", "title": "代码答辩", "prompt": decision["follow_up"]},
            question_id=qid, round_index=parent["round_index"], round_type="oral",
            round_weight=parent["round_weight"], timebox_minutes=1, skills=tuple(parent["skills"]),
            plan_context_sha256=context_sha)
        question.update(stage="coding", parent_coding_question_id=parent["question_id"])
        session["questions"].append(question)
        d["question_ids"].append(qid)
        d["status"] = "answering"
        session["timeline"].append({"event": "question_generated", "question_id": qid, "timestamp": ri._timestamp(now)})
    else:
        if decision["transition_reason"] not in ("sufficient", "identified_error", "confirmed_unknown"):
            raise ValueError("答辩收尾必须说明已有证据或已确认的边界。")
        targets = {p["claim_id"] for p in session["interviewer_state"]["probes"] if p["question_id"] in d["question_ids"]}
        if any(merged["gaps"][key]["status"] != "closed" and merged["claims"][key]["criterion_status"] != "model_supported" for key in targets):
            raise ValueError("答辩目标仍未取证或关闭，不能仅声明充分就结束。")
        close(session, decision["transition_reason"], remaining)
    session["interviewer_state"] = merged
    session.setdefault("turn_decisions", {})[question_id] = {
        "next_stage": decision["next_stage"], "state_revision": merged["revision"],
        "context_sha256": context_sha, "sent_answer_sources": contract["sent_answer_sources"],
        "expert_references": [{k: r[k] for k in ("topic_id", "criterion", "version", "sha256")}
                              for r in contract.get("expert_references", [])],
        "methods": [{k: m[k] for k in ("id", "version", "sha256", "path")} for m in contract["methods"]]}
    ri._end_ai_wait(session, now)
    ri._save(repo_root, profile_id, session)
    return session
