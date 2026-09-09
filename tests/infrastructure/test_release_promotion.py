"""Publishing must reuse accepted artifacts, never an untested application build."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("promotion", ROOT / "scripts/verify_release_promotion.py")
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)
MANIFEST = json.loads((ROOT / ".github/release-manifest.json").read_text("utf-8"))


def evidence():
    run = {"id": MANIFEST["run_id"], "head_sha": MANIFEST["source_commit"],
           "repository": {"full_name": promotion.REPO}, "path": ".github/workflows/ci.yml",
           "event": "push", "status": "completed", "conclusion": "success"}
    jobs = {"jobs": [{"name": name, "conclusion": "success"} for name in sorted(promotion.REQUIRED_JOBS)]}
    artifacts = {"artifacts": [{"id": int(id), "name": name, "expired": False}
                               for id, name in MANIFEST["artifacts"].items()]}
    return run, jobs, artifacts


def test_all_ten_gates_and_exact_artifacts_are_required():
    run, jobs, artifacts = evidence()
    assert len(jobs["jobs"]) == 10
    promotion.check_ci(MANIFEST, run, jobs, artifacts)
    for job in jobs["jobs"]:
        job["conclusion"] = "skipped"
        with pytest.raises(RuntimeError, match="Every"):
            promotion.check_ci(MANIFEST, run, jobs, artifacts)
        job["conclusion"] = "success"
    artifacts["artifacts"][0]["expired"] = True
    with pytest.raises(RuntimeError, match="expired"):
        promotion.check_ci(MANIFEST, run, jobs, artifacts)


@pytest.mark.parametrize("field,value", [("conclusion", "failure"), ("head_sha", "wrong"),
                                        ("event", "pull_request"), ("path", "untrusted.yml")])
def test_failed_or_unrelated_ci_is_rejected(field, value):
    run, jobs, artifacts = evidence()
    run[field] = value
    with pytest.raises(RuntimeError, match="CI"):
        promotion.check_ci(MANIFEST, run, jobs, artifacts)


@pytest.mark.parametrize("path", ["src/llm_interview_lab/desktop/main.py", "pyproject.toml",
                                 "curriculum/catalog/foundation.yaml", "AGENTS.md",
                                 "scripts/build_windows_desktop.py", ".github/workflows/ci.yml"])
def test_application_and_build_changes_need_new_build(path):
    with pytest.raises(RuntimeError, match="Build inputs"):
        promotion.check_changed_paths(["README.md", path])


def test_documentation_only_promotion_and_asset_integrity(tmp_path):
    promotion.check_changed_paths(["README.md", "docs/windows.md", "plans/completed/example.md",
                                   ".github/workflows/publish.yml"])
    manifest = copy.deepcopy(MANIFEST)
    for name in manifest["assets"]:
        data = ("synthetic " + name).encode()
        (tmp_path / name).write_bytes(data)
        manifest["assets"][name] = hashlib.sha256(data).hexdigest()
    promotion.check_assets(manifest, tmp_path)
    (tmp_path / next(iter(manifest["assets"]))).write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="differs"):
        promotion.check_assets(manifest, tmp_path)


def test_publish_requires_tag_main_ci_and_draft_upload_before_visibility():
    workflow = (ROOT / ".github/workflows/publish.yml").read_text("utf-8")
    assert "github.event.ref_type == 'tag'" in workflow
    assert "git merge-base --is-ancestor HEAD origin/main" in workflow
    assert "--check-ci" in workflow and "--assets dist/release" in workflow
    assert "artifact-ids:" in workflow and "--verify-tag" in workflow
    assert workflow.index("--draft --verify-tag") < workflow.index("--draft=false")
    assert "--clobber" not in workflow
