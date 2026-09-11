"""Four actual service transactions per track, with scripted decisions only."""
from copy import deepcopy
from datetime import datetime, timedelta
import pytest
from tests.infrastructure.test_interviewer_evidence import public_repo, unified, new_v3, context, packet, commit
from llm_interview_lab.role_interviews import RoleInterviewError, advance_dynamic_role_interview
from llm_interview_lab.interview_flow import flow_coverage


@pytest.mark.parametrize("track", ["resolved_to_new_criterion", "unknown_adjacent", "contradiction_resolution", "time_transition", "restart_retry"])
def test_four_round_evidence_trajectories(unified, track):
    service, profile = unified
    iid = new_v3(service, profile)
    target = "claim-0001"
    criterion = "mechanism"
    for index in range(4):
        qid = f"q-{index + 1:03d}"
        answer = "我负责组内优势计算，GRPO按奖励组处理。"
        if track == "unknown_adjacent" and index in (1, 2):
            answer += "这部分我不知道，换成具体输入后也无法解释。"
        if track == "contradiction_resolution":
            answer += "系数是0.3。" if index == 0 else "系数是0.8。"
            if index >= 2:
                answer += "前一个是实验A，后一个是实验B，不是同一次运行。"
        service.answer_interview(profile, iid, qid, answer)
        c = context(service, profile, iid, answer)
        value = packet(c, intro=index == 0, criterion=criterion,
            claim_ref="new:claim" if index == 0 else target,
            experience_ref="new:exp" if index == 0 else "exp-0001")
        value["follow_up"] = "你提到组内优势计算，接下来能沿实际输入解释当前这一步如何更新吗？"
        if track == "unknown_adjacent" and index in (1, 2):
            value["state_update"]["claims"][0]["status"] = "explicit_unknown"
            value["probe"]["action"] = "adjacent"
        if track in ("resolved_to_new_criterion", "unknown_adjacent") and index == 2:
            status = "model_supported" if track == "resolved_to_new_criterion" else "explicit_unknown"
            value["state_update"]["claims"][0]["status"] = status
            if status == "explicit_unknown":
                value["state_update"]["closures"] = [{"claim_ref": target, "reason": "confirmed_unknown",
                    "evidence": {"question_id": qid, "quote": "这部分我不知道"}}]
            other = deepcopy(value["state_update"]["claims"][0])
            other.update(ref="new:ratio", criterion="ratio", status="unassessed", statement="概率比更新待核实")
            value["state_update"]["claims"].append(other)
            value["probe"].update(claim_ref="new:ratio", criterion="ratio", action="change_angle")
        if track == "contradiction_resolution" and index in (1, 2):
            value["state_update"]["claims"][0]["status"] = "disputed" if index == 1 else "partial"
            value["state_update"]["contradictions"] = [{"claim_ref": target,
                "first": {"question_id": "q-001", "quote": "系数是0.3"},
                "second": {"question_id": qid, "quote": "系数是0.8" if index == 1 else "前一个是实验A，后一个是实验B"},
                "ambiguity": "是否同一次运行", "resolved": index == 2,
                "resolution": "候选人明确说明两次实验不同；正确性仍待核实。" if index == 2 else ""}]
        if track == "restart_retry" and index == 1:
            invalid = deepcopy(value)
            invalid["state_update"]["claims"][0]["evidence"]["quote"] = "伪造的引文"
            with pytest.raises(RoleInterviewError):
                commit(service, profile, iid, c, invalid)
            service = type(service)(service.repo_root)
            assert context(service, profile, iid, answer) == c
        if track == "time_transition" and index >= 2:
            value.update(next_stage="theory", transition_reason="time_deferred" if index == 2 else "continue")
            value["probe"]["action"] = "transition" if index == 2 else "inspect"
            started = datetime.fromisoformat(service.interview_session(profile, iid)["started_at"].replace("Z", "+00:00"))
            result = advance_dynamic_role_interview(service.repo_root, profile, iid, service.catalog, service.roles,
                qid, value, context_sha256="b" * 64, request_contract=c, now=started + timedelta(minutes=28 + index))
        else:
            result = commit(service, profile, iid, c, value)
        assert result["interviewer_state"]["revision"] == index + 1
        if track in ("resolved_to_new_criterion", "unknown_adjacent") and index == 2:
            target, criterion = "claim-0002", "ratio"
    assert len(result["questions"]) == 5
    if track == "unknown_adjacent":
        assert not flow_coverage(result)["experience_angles"]
    if track == "contradiction_resolution":
        assert result["interviewer_state"]["contradictions"]["claim-0001"]["resolved"]
    if track == "time_transition":
        assert flow_coverage(result)["unresolved_gaps"]
