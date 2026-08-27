from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from llm_interview_lab.catalog import CatalogError, load_catalog
from llm_interview_lab.cli import main
from llm_interview_lab.events import append_event, read_events, reduce_events
from llm_interview_lab.workspace import event_schema_path, profile_paths
from scripts.record_field_run import FieldRunError, record_field_run


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
QUEST_IDS = ("FND-001", "FND-002", "FND-003", "FND-004", "FND-005", "FND-006")


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    for name in ("pyproject.toml", ".gitignore"):
        shutil.copy2(REPO_ROOT / name, root / name)
    for name in ("schema", "catalog", "problems", "retention"):
        shutil.copytree(REPO_ROOT / "curriculum" / name, root / "curriculum" / name)
    for name in ("schema", "templates", "demo"):
        shutil.copytree(REPO_ROOT / "workspace" / name, root / "workspace" / name)
    (root / "workspace/profiles").mkdir(parents=True)
    (root / "workspace/profiles/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _master(repo_root: Path, profile_id: str, problem_id: str) -> None:
    paths = profile_paths(repo_root, profile_id)
    schema = event_schema_path(repo_root)
    attempt_id = "attempt-0001"
    digest = hashlib.sha256(problem_id.encode()).hexdigest()
    append_event(
        paths.events_file,
        schema,
        profile_id=profile_id,
        event_type="task_started",
        problem_id=problem_id,
        attempt_id=attempt_id,
        payload={"submission_relpath": f"workspace/profiles/{profile_id}/submissions/{problem_id}/evidence.py"},
    )
    append_event(
        paths.events_file,
        schema,
        profile_id=profile_id,
        event_type="task_mastered",
        problem_id=problem_id,
        attempt_id=attempt_id,
        payload={"submission_sha256": digest},
    )


def test_fresh_profile_starts_at_first_golden_node(tmp_path, monkeypatch, capsys):
    root = _repository(tmp_path); monkeypatch.chdir(root)
    assert main(["init", "--profile", "learner-one"]) == 0
    capsys.readouterr()
    assert main(["next", "--profile", "learner-one"]) == 0
    output = capsys.readouterr().out
    assert "FND-001 Wrong Prediction Count" in output
    assert "FND-002 Sample Contract Validation" not in output


def test_each_mastery_unlocks_only_the_next_golden_node(tmp_path, monkeypatch, capsys):
    root = _repository(tmp_path); monkeypatch.chdir(root)
    main(["init", "--profile", "learner-one"]); capsys.readouterr()
    for index, problem_id in enumerate(QUEST_IDS[:-1]):
        _master(root, "learner-one", problem_id)
        assert main(["next", "--profile", "learner-one"]) == 0
        output = capsys.readouterr().out
        assert QUEST_IDS[index + 1] in output
        if index + 2 < len(QUEST_IDS):
            assert QUEST_IDS[index + 2] not in output


def test_capstone_unlocks_only_after_all_six_are_mastered(tmp_path, monkeypatch, capsys):
    root = _repository(tmp_path); monkeypatch.chdir(root)
    main(["init", "--profile", "learner-one"]); capsys.readouterr()
    for problem_id in QUEST_IDS[:-1]:
        _master(root, "learner-one", problem_id)
    main(["next", "--profile", "learner-one"])
    assert "CAP-FND-001" not in capsys.readouterr().out
    _master(root, "learner-one", QUEST_IDS[-1])
    main(["next", "--profile", "learner-one"])
    assert "CAP-FND-001 Hard Sample Data Pipeline" in capsys.readouterr().out
    assert main(["start", "CAP-FND-001", "--profile", "learner-one"]) == 0


def test_contract_nodes_need_explicit_or_profile_opt_in(tmp_path, monkeypatch, capsys):
    root = _repository(tmp_path); monkeypatch.chdir(root)
    main(["init", "--profile", "learner-one"]); capsys.readouterr()
    for problem_id in QUEST_IDS:
        _master(root, "learner-one", problem_id)
    experimental_problem = "AGT-001"
    assert main(["start", experimental_problem, "--profile", "learner-one"]) == 2
    assert "contract-only" in capsys.readouterr().err
    assert main(["start", experimental_problem, "--profile", "learner-one", "--allow-experimental"]) == 0

    main(["init", "--profile", "learner-two"]); capsys.readouterr()
    profile_file = profile_paths(root, "learner-two").profile_file
    profile = yaml.safe_load(profile_file.read_text(encoding="utf-8"))
    profile["preferences"]["allow_experimental_problems"] = True
    profile_file.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    for problem_id in QUEST_IDS:
        _master(root, "learner-two", problem_id)
    assert main(["start", experimental_problem, "--profile", "learner-two"]) == 0


def test_default_planner_contains_only_validated_nodes():
    catalog = load_catalog(REPO_ROOT)
    mastered = set(QUEST_IDS)
    default_ids = {problem.id for problem in catalog.unlocked(mastered)}
    experimental_ids = {
        problem.id for problem in catalog.unlocked(mastered, include_experimental=True)
    }
    assert default_ids and all(catalog.get(problem_id).recommendable for problem_id in default_ids)
    assert "TNS-002" in default_ids
    assert "AGT-001" not in default_ids and "AGT-001" in experimental_ids


def test_oracle_fingerprint_invalidates_changed_base_or_retention_asset(tmp_path):
    root = _repository(tmp_path)
    task = root / "curriculum/problems/FND-001-wrong-prediction-count/task.md"
    task.write_text(task.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="stale Oracle validation fingerprint: FND-001"):
        load_catalog(root)

    root = _repository(tmp_path / "third")
    shard = root / "curriculum/catalog/foundation.yaml"
    text = shard.read_text(encoding="utf-8")
    shard.write_text(text.replace("title: Wrong Prediction Count", "title: Changed Contract", 1), encoding="utf-8")
    with pytest.raises(CatalogError, match="stale Oracle validation fingerprint: FND-001"):
        load_catalog(root)

    root = _repository(tmp_path / "second")
    retention = root / "curriculum/retention/FND-001/d2/test_public.py"
    retention.write_text(retention.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="stale Oracle validation fingerprint: FND-001"):
        load_catalog(root)


def test_profiles_remain_independent_through_golden_progress(tmp_path, monkeypatch):
    root = _repository(tmp_path); monkeypatch.chdir(root)
    main(["init", "--profile", "learner-one"]); main(["init", "--profile", "learner-two"])
    _master(root, "learner-one", "FND-001")
    one = reduce_events(read_events(profile_paths(root, "learner-one").events_file, event_schema_path(root)))
    two = reduce_events(read_events(profile_paths(root, "learner-two").events_file, event_schema_path(root)))
    assert one.problem_status("FND-001") == "mastered"
    assert two.problem_status("FND-001") == "not_started"


def test_field_run_is_anonymous_idempotent_and_aggregated_only_in_temp_repo(tmp_path):
    root = _repository(tmp_path)
    record = record_field_run(
        root,
        anonymous_run_id="run-alpha-001",
        problem_id="FND-001",
        quest_id="python_data_reliability",
        completion_status="completed",
        issue_count=0,
        validation_date="2026-08-27",
    )
    assert set(record) == {
        "schema_version", "anonymous_run_id", "problem_id", "quest_id",
        "completion_status", "issue_count", "validation_date",
    }
    problem = load_catalog(root).get("FND-001")
    assert problem.validation_level == "field" and problem.field_runs == 1
    with pytest.raises(FieldRunError, match="already recorded"):
        record_field_run(
            root,
            anonymous_run_id="run-alpha-001",
            problem_id="FND-001",
            quest_id="python_data_reliability",
            completion_status="completed",
            issue_count=0,
            validation_date="2026-08-27",
        )


def test_six_golden_nodes_are_oracle_and_retention_ready():
    catalog = load_catalog(REPO_ROOT)
    for problem_id in QUEST_IDS:
        problem = catalog.get(problem_id)
        assert problem.validation_level in {"oracle", "field", "stable"}
        assert all(problem.retention_variant(REPO_ROOT, stage) for stage in ("d2", "d7"))
    capstone = catalog.get("CAP-FND-001")
    assert capstone.validation_level == "oracle"
    assert set(capstone.prerequisites) == set(QUEST_IDS)


def test_golden_retention_assets_are_distinct_from_base_and_each_other():
    catalog = load_catalog(REPO_ROOT)
    for problem_id in QUEST_IDS:
        problem = catalog.get(problem_id)
        d2 = problem.retention_variant(REPO_ROOT, "d2")
        d7 = problem.retention_variant(REPO_ROOT, "d7")
        assert d2 is not None and d7 is not None and problem.problem_dir is not None
        starter_paths = {problem.problem_dir / "starter.py", d2[0], d7[0]}
        test_paths = {problem.public_tests, d2[1], d7[1]}
        assert len(starter_paths) == 3 and len(test_paths) == 3
        assert len({path.read_bytes() for path in starter_paths}) == 3
        assert len({path.read_bytes() for path in test_paths}) == 3


def test_catalog_and_show_expose_quality_markers(monkeypatch, capsys):
    monkeypatch.chdir(REPO_ROOT)
    assert main(["show", "FND-001"]) == 0
    shown = capsys.readouterr().out
    assert "ASSETS  ready" in shown
    assert "VALIDATION  oracle" in shown
    assert "RETENTION  yes" in shown
    assert "FIELD RUNS  0" in shown
    assert main(["catalog", "--track", "ai_foundation"]) == 0
    listing = capsys.readouterr().out
    assert "FND-001" in listing and "validation=oracle retention=yes field_runs=0" in listing
    assert "TNS-002" in listing and "validation=contract" in listing
