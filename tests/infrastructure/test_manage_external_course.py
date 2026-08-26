from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.manage_external_course import (
    AUDITED_REMOTE_REF,
    CheckoutStatus,
    LEARNER_BRANCH,
    ExternalCourseError,
    _git_environment,
    _is_link_or_reparse,
    _normalize_git_url,
    _print_status,
    _redact_git_location,
    checkout_target,
    inspect_checkout,
    install_checkout,
    load_assignment_sources,
    main,
)


pytestmark = [pytest.mark.infrastructure]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(cwd: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _local_remote(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "official-source"
    source.mkdir()
    _git(source, "init")
    _git(source, "config", "user.name", "External Course Test")
    _git(source, "config", "user.email", "external-course-test@example.invalid")
    (source / "assignment.txt").write_text("starter\n", encoding="utf-8")
    _git(source, "add", "assignment.txt")
    _git(source, "commit", "-m", "create audited assignment")
    return source, _git(source, "rev-parse", "HEAD")


def _metadata_repo(tmp_path: Path) -> Path:
    metadata_root = tmp_path / "repository"
    shutil.copytree(
        REPO_ROOT / "curriculum" / "external",
        metadata_root / "curriculum" / "external",
    )
    shutil.copytree(REPO_ROOT / "references", metadata_root / "references")
    return metadata_root


def test_sources_resolve_only_below_ignored_external_root() -> None:
    sources = load_assignment_sources(repo_root=REPO_ROOT)

    assert list(sources) == [
        "EXT-CS336-A1",
        "EXT-CS336-A2",
        "EXT-CS336-A3",
        "EXT-CS336-A4",
        "EXT-CS336-A5",
    ]
    external_root = (REPO_ROOT / ".external").resolve()
    for source in sources.values():
        target = checkout_target(source, repo_root=REPO_ROOT)
        assert target.is_relative_to(external_root)
        assert target != external_root


def test_checkout_target_rejects_linked_external_root(tmp_path: Path) -> None:
    metadata_root = _metadata_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (metadata_root / ".external").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlink creation unavailable: {error}")
    source = load_assignment_sources(repo_root=metadata_root)["EXT-CS336-A1"]

    with pytest.raises(ExternalCourseError, match="link or reparse point"):
        checkout_target(source, repo_root=metadata_root)


def test_cli_refuses_install_without_explicit_policy_acknowledgement(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_root = _metadata_repo(tmp_path)
    exit_code = main(
        ["install", "EXT-CS336-A1"],
        repo_root=metadata_root,
    )

    assert exit_code == 2
    assert "Refusing installation" in capsys.readouterr().err
    assert not (metadata_root / ".external").exists()


@pytest.mark.parametrize("assignment_id", ["EXT-CS336-A2", "EXT-CS336-A4"])
def test_cli_refuses_spoiler_checkout_without_separate_acknowledgement(
    assignment_id: str,
    tmp_path: Path,
    capsys,
) -> None:
    metadata_root = _metadata_repo(tmp_path)

    exit_code = main(
        ["install", assignment_id, "--acknowledge-policy"],
        repo_root=metadata_root,
    )

    assert exit_code == 2
    error = capsys.readouterr().err
    assert "contains material for EXT-CS336-A1" in error
    assert "--acknowledge-spoilers" in error
    assert not (metadata_root / ".external").exists()


def test_cli_show_and_list_disclose_governance_and_machine_labels(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_root = _metadata_repo(tmp_path)

    assert main(["list"], repo_root=metadata_root) == 0
    listing = capsys.readouterr().out
    assert "not affiliated with Stanford University" in listing
    assert "license=verified" in listing
    assert "integration=inventory-audited" in listing
    assert "checkout=missing" in listing

    assert main(["show", "EXT-CS336-A2"], repo_root=metadata_root) == 0
    detail = capsys.readouterr().out
    assert "academic-integrity policy:" in detail
    assert "license evidence:" in detail
    assert "license audit method:" in detail
    assert "spoiler warning: contains material for EXT-CS336-A1" in detail
    assert "runtime tiers:" in detail
    assert "EXT-CS336-A2-flash-attention" in detail
    assert "selection mode: preview-only" in detail


def test_cli_list_and_show_json_are_machine_readable_and_path_safe(
    tmp_path: Path,
    capsys,
) -> None:
    metadata_root = _metadata_repo(tmp_path)

    assert main(["list", "--json"], repo_root=metadata_root) == 0
    listing_text = capsys.readouterr().out
    listing = json.loads(listing_text)
    assert listing["schema_version"] == 1
    assert listing["ok"] is True
    assert len(listing["assignments"]) == 5
    assert listing["assignments"][0]["checkout_state"] == "missing"
    assert str(metadata_root.resolve()) not in listing_text

    assert main(["show", "EXT-CS336-A5", "--json"], repo_root=metadata_root) == 0
    detail_text = capsys.readouterr().out
    detail = json.loads(detail_text)["assignment"]
    assert detail["license"]["status"] == "not-found"
    assert detail["academic_integrity"]["maximum_ai_help"] == "H2"
    assert detail["selection_mode"] == "preview-only"
    assert detail["inventory"] == {
        "adapters": 12,
        "problem_kinds": {"analysis": 9, "coding": 17, "experiment": 18},
        "problems": 44,
        "test_nodes": 21,
    }
    assert str(metadata_root.resolve()) not in detail_text

    assert (
        main(
            ["show-group", "EXT-CS336-A2-ddp", "--json"],
            repo_root=metadata_root,
        )
        == 0
    )
    group_text = capsys.readouterr().out
    group = json.loads(group_text)["problem_group_task"]
    assert group["canonical_task_id"] == "EXT-CS336-A2-ddp"
    assert group["completion_role"] == "portable-elective"
    assert group["companion_runtime"] == "cpu-contract"
    assert group["official_runtime"] == "multi-gpu"
    assert group["selection_mode"] == "preview-only"
    assert group["prerequisites"] == []
    assert group["problem_ids"]
    assert group["capabilities"]
    assert group["acceptance_evidence"]
    assert group["related_test_commands"]
    assert group["status_contract"]["learner_status_scope"] == "companion-runtime-only"
    assert "all portable-required" in group["status_contract"]["portable_aggregate_reviewed"]
    assert "retained_7d" in group["status_contract"]["portable_aggregate_retained_7d"]
    assert "mastered" in group["status_contract"]["portable_aggregate_mastered"]
    assert "never implied" in group["status_contract"]["official_execution"]
    assert str(metadata_root.resolve()) not in group_text


def test_install_cli_does_not_offer_all_assignments(capsys) -> None:
    with pytest.raises(SystemExit) as error:
        main(["install", "EXT-CS336-A1", "--all", "--acknowledge-policy"])

    assert error.value.code == 2
    assert "--all" in capsys.readouterr().err


def test_install_checkout_pins_identity_disables_push_and_preserves_learner_work(
    tmp_path: Path,
) -> None:
    source, revision = _local_remote(tmp_path)
    target = tmp_path / "external" / "assignment"

    status = install_checkout(
        source_url=str(source),
        revision=revision,
        target=target,
    )

    assert status.source_valid
    assert status.base_revision == revision
    assert status.head_revision == revision
    assert status.branch == LEARNER_BRANCH
    assert status.push_url == "DISABLED"
    assert status.dirty is None
    assert _git(target, "config", "--get-all", "remote.origin.fetch") == (
        f"+{revision}:{AUDITED_REMOTE_REF}"
    )
    assert _git(
        target,
        "for-each-ref",
        "--format=%(refname)",
        "refs/remotes/origin",
    ) == AUDITED_REMOTE_REF
    assert _git(target, "for-each-ref", "--format=%(refname)", "refs/tags") == ""

    _git(target, "config", "user.name", "Learner")
    _git(target, "config", "user.email", "learner@example.invalid")
    (target / "answer.txt").write_text("independent attempt\n", encoding="utf-8")
    _git(target, "add", "answer.txt")
    _git(target, "commit", "-m", "record learner attempt")
    (target / "answer.txt").write_text("independent attempt\nrevision\n", encoding="utf-8")

    after_work = inspect_checkout(
        target=target,
        expected_url=str(source),
        expected_revision=revision,
    )
    assert after_work.source_valid
    assert after_work.head_revision != revision
    assert after_work.dirty is None


def test_inspection_rejects_executable_local_config_without_scanning_worktree(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import scripts.manage_external_course as manager

    source, revision = _local_remote(tmp_path)
    target = tmp_path / "external" / "assignment"
    install_checkout(source_url=str(source), revision=revision, target=target)
    _git(target, "config", "core.fsmonitor", "attacker-controlled-command")
    calls: list[tuple[str, ...]] = []
    original = manager._run_git

    def recording_run_git(arguments, **kwargs):
        calls.append(tuple(arguments))
        return original(arguments, **kwargs)

    monkeypatch.setattr(manager, "_run_git", recording_run_git)

    status = inspect_checkout(
        target=target,
        expected_url=str(source),
        expected_revision=revision,
    )

    assert not status.source_valid
    assert status.dirty is None
    assert all(not arguments or arguments[0] != "status" for arguments in calls)


def test_install_fetches_only_audited_revision_not_newer_upstream_history(
    tmp_path: Path,
) -> None:
    source, audited_revision = _local_remote(tmp_path)
    (source / "assignment.txt").write_text("starter\nnew upstream work\n", encoding="utf-8")
    _git(source, "add", "assignment.txt")
    _git(source, "commit", "-m", "unreviewed upstream change")
    unreviewed_revision = _git(source, "rev-parse", "HEAD")
    target = tmp_path / "external" / "assignment"

    install_checkout(
        source_url=str(source),
        revision=audited_revision,
        target=target,
    )

    result = subprocess.run(
        ["git", "cat-file", "-e", f"{unreviewed_revision}^{{commit}}"],
        cwd=target,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode != 0


def test_install_checkout_refuses_overwrite_and_detects_source_tampering(
    tmp_path: Path,
) -> None:
    source, revision = _local_remote(tmp_path)
    target = tmp_path / "external" / "assignment"
    install_checkout(source_url=str(source), revision=revision, target=target)

    with pytest.raises(ExternalCourseError, match="refusing to overwrite"):
        install_checkout(source_url=str(source), revision=revision, target=target)

    _git(target, "config", "llmInterviewLab.upstreamRevision", "0" * 40)
    tampered = inspect_checkout(
        target=target,
        expected_url=str(source),
        expected_revision=revision,
    )
    assert not tampered.source_valid
    assert tampered.message == "source identity mismatch"


@pytest.mark.parametrize("key", ["remote.origin.url", "remote.origin.pushurl"])
def test_checkout_rejects_ambiguous_multi_value_remote_configuration(
    tmp_path: Path,
    key: str,
) -> None:
    source, revision = _local_remote(tmp_path)
    target = tmp_path / "external" / "assignment"
    install_checkout(source_url=str(source), revision=revision, target=target)
    _git(target, "config", "--add", key, "https://example.invalid/untrusted.git")

    status = inspect_checkout(
        target=target,
        expected_url=str(source),
        expected_revision=revision,
    )

    assert not status.source_valid
    assert "must contain exactly one value" in status.message


@pytest.mark.parametrize("rewrite_key", ["insteadOf", "pushInsteadOf"])
def test_checkout_rejects_transport_url_rewrite_configuration(
    tmp_path: Path,
    rewrite_key: str,
) -> None:
    source, revision = _local_remote(tmp_path)
    target = tmp_path / "external" / "assignment"
    install_checkout(source_url=str(source), revision=revision, target=target)
    _git(
        target,
        "config",
        f"url.https://attacker.invalid/exfil.{rewrite_key}",
        "DISABLED",
    )

    status = inspect_checkout(
        target=target,
        expected_url=str(source),
        expected_revision=revision,
    )

    assert not status.source_valid
    assert status.message == "source identity mismatch"


def test_checkout_rejects_unreviewed_remote_refs_and_tags(tmp_path: Path) -> None:
    source, revision = _local_remote(tmp_path)
    target = tmp_path / "external" / "assignment"
    install_checkout(source_url=str(source), revision=revision, target=target)

    _git(target, "update-ref", "refs/remotes/origin/unreviewed", revision)
    with_remote_ref = inspect_checkout(
        target=target,
        expected_url=str(source),
        expected_revision=revision,
    )
    assert not with_remote_ref.source_valid

    _git(target, "update-ref", "-d", "refs/remotes/origin/unreviewed")
    _git(target, "tag", "unreviewed", revision)
    with_tag = inspect_checkout(
        target=target,
        expected_url=str(source),
        expected_revision=revision,
    )
    assert not with_tag.source_valid


def test_checkout_rejects_audited_remote_ref_retargeting(tmp_path: Path) -> None:
    source, revision = _local_remote(tmp_path)
    target = tmp_path / "external" / "assignment"
    install_checkout(source_url=str(source), revision=revision, target=target)
    _git(target, "config", "user.name", "Learner")
    _git(target, "config", "user.email", "learner@example.invalid")
    (target / "learner.txt").write_text("learner work\n", encoding="utf-8")
    _git(target, "add", "learner.txt")
    _git(target, "commit", "-m", "learner commit")
    learner_revision = _git(target, "rev-parse", "HEAD")

    _git(target, "update-ref", AUDITED_REMOTE_REF, learner_revision)
    status = inspect_checkout(
        target=target,
        expected_url=str(source),
        expected_revision=revision,
    )

    assert not status.source_valid
    assert status.message == "source identity mismatch"


def test_checkout_rejects_replace_refs_and_object_indirection(tmp_path: Path) -> None:
    source, revision = _local_remote(tmp_path)
    replace_target = tmp_path / "external" / "replace-assignment"
    install_checkout(source_url=str(source), revision=revision, target=replace_target)
    _git(replace_target, "config", "user.name", "Learner")
    _git(replace_target, "config", "user.email", "learner@example.invalid")
    (replace_target / "learner.txt").write_text("learner work\n", encoding="utf-8")
    _git(replace_target, "add", "learner.txt")
    _git(replace_target, "commit", "-m", "learner commit")
    learner_revision = _git(replace_target, "rev-parse", "HEAD")
    _git(replace_target, "replace", revision, learner_revision)

    replaced = inspect_checkout(
        target=replace_target,
        expected_url=str(source),
        expected_revision=revision,
    )
    assert not replaced.source_valid

    alternate_target = tmp_path / "external" / "alternate-assignment"
    install_checkout(source_url=str(source), revision=revision, target=alternate_target)
    alternates = alternate_target / ".git" / "objects" / "info" / "alternates"
    alternates.write_text(str(source / ".git" / "objects") + "\n", encoding="utf-8")

    redirected = inspect_checkout(
        target=alternate_target,
        expected_url=str(source),
        expected_revision=revision,
    )
    assert not redirected.source_valid
    assert redirected.message == "target is not an independent regular Git checkout"

    common_target = tmp_path / "external" / "common-assignment"
    install_checkout(source_url=str(source), revision=revision, target=common_target)
    (common_target / ".git" / "commondir").write_text("../outside\n", encoding="utf-8")
    common = inspect_checkout(
        target=common_target,
        expected_url=str(source),
        expected_revision=revision,
    )
    assert not common.source_valid
    assert common.message == "target is not an independent regular Git checkout"


def test_plain_child_directory_cannot_inherit_parent_git_identity(tmp_path: Path) -> None:
    parent, revision = _local_remote(tmp_path)
    child = parent / "not-an-independent-checkout"
    child.mkdir()

    status = inspect_checkout(
        target=child,
        expected_url=str(parent),
        expected_revision=revision,
    )

    assert status.installed
    assert not status.source_valid
    assert status.message == "target is not an independent regular Git checkout"


def test_missing_checkout_is_reported_without_mutation(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    status = inspect_checkout(
        target=missing,
        expected_url="https://example.invalid/course",
        expected_revision="1" * 40,
    )

    assert not status.installed
    assert not status.source_valid
    assert status.message == "not installed"
    assert not missing.exists()


def test_git_location_redaction_fails_closed_for_credentials_and_bad_ports() -> None:
    secret_url = "https://user:secret@example.invalid:bad/repo?token=also-secret#fragment"

    redacted = _redact_git_location(secret_url)

    assert "secret" not in redacted
    assert "user" not in redacted
    assert "token" not in redacted
    assert redacted == "https://redacted-host/repo"


def test_status_never_echoes_untrusted_remote_values(tmp_path: Path, capsys) -> None:
    metadata_root = _metadata_repo(tmp_path)
    source = load_assignment_sources(repo_root=metadata_root)["EXT-CS336-A1"]
    status = CheckoutStatus(
        installed=True,
        source_valid=False,
        target=metadata_root / ".external" / "assignment",
        expected_revision=source.revision,
        fetch_url="https:user:secret@example.invalid/token-in-path",
        push_url="secret-push-target",
        message="source identity mismatch",
    )

    _print_status(source, status, repo_root=metadata_root)
    output = capsys.readouterr().out

    assert "secret" not in output
    assert "token-in-path" not in output
    assert "mismatch (value hidden)" in output


def test_cli_errors_redact_repository_absolute_path(tmp_path: Path, capsys) -> None:
    metadata_root = _metadata_repo(tmp_path)
    source = load_assignment_sources(repo_root=metadata_root)["EXT-CS336-A1"]
    target = checkout_target(source, repo_root=metadata_root)
    target.mkdir(parents=True)

    exit_code = main(
        ["install", "EXT-CS336-A1", "--acknowledge-policy"],
        repo_root=metadata_root,
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "<repository>" in captured.err
    assert str(metadata_root.resolve()) not in captured.err


def test_git_url_normalization_preserves_case_sensitive_repository_paths() -> None:
    assert _normalize_git_url("HTTPS://GitHub.COM/Owner/Repo.git/") == (
        "https://github.com/Owner/Repo"
    )
    assert _normalize_git_url("https://github.com/Owner/Repo") != _normalize_git_url(
        "https://github.com/owner/repo"
    )


def test_git_environment_rejects_inherited_repository_and_config_injection(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "attacker-controlled")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "remote.origin.fetch")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "+refs/heads/*:refs/remotes/origin/*")
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "'core.hooksPath=attacker-controlled'")
    monkeypatch.setenv("GIT_TRACE", "attacker-controlled")
    monkeypatch.setenv("GIT_SSH_COMMAND", "attacker-controlled")
    monkeypatch.setenv("GIT_TEMPLATE_DIR", "attacker-controlled")

    environment = _git_environment()

    assert "GIT_DIR" not in environment
    assert "GIT_CONFIG_COUNT" not in environment
    assert "GIT_CONFIG_KEY_0" not in environment
    assert "GIT_CONFIG_VALUE_0" not in environment
    assert "GIT_CONFIG_PARAMETERS" not in environment
    assert "GIT_TRACE" not in environment
    assert "GIT_SSH_COMMAND" not in environment
    assert "GIT_TEMPLATE_DIR" not in environment
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_CONFIG_GLOBAL"]
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_LFS_SKIP_SMUDGE"] == "1"
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"


def test_status_uses_repository_relative_path(tmp_path: Path, capsys) -> None:
    metadata_root = _metadata_repo(tmp_path)

    assert main(["status", "EXT-CS336-A1"], repo_root=metadata_root) == 0
    output = capsys.readouterr().out

    assert "target: .external/stanford-cs336/assignment1-basics" in output
    assert str(metadata_root.resolve()) not in output

    assert main(["commands", "EXT-CS336-A1"], repo_root=metadata_root) == 0
    commands_output = capsys.readouterr().out
    assert "Checkout: .external/stanford-cs336/assignment1-basics" in commands_output
    assert str(metadata_root.resolve()) not in commands_output


def test_windows_reparse_attribute_is_rejected_without_privileged_symlink(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class ReparseStat:
        st_mode = 0
        st_file_attributes = 0x400

    monkeypatch.setattr("scripts.manage_external_course.os.lstat", lambda _: ReparseStat())

    assert _is_link_or_reparse(tmp_path / "simulated-junction")


def test_cli_reports_stale_metadata_without_traceback(tmp_path: Path, capsys) -> None:
    metadata_root = _metadata_repo(tmp_path)
    navigation = metadata_root / "curriculum" / "external" / "NAVIGATION.md"
    navigation.write_text(
        navigation.read_text(encoding="utf-8") + "\nstale\n",
        encoding="utf-8",
    )

    exit_code = main(["list"], repo_root=metadata_root)

    assert exit_code == 1
    error = capsys.readouterr().err
    assert error.startswith("ERROR:")
    assert "Traceback" not in error


def test_cli_json_reports_stale_metadata_as_json(tmp_path: Path, capsys) -> None:
    metadata_root = _metadata_repo(tmp_path)
    navigation = metadata_root / "curriculum" / "external" / "NAVIGATION.md"
    navigation.write_text(
        navigation.read_text(encoding="utf-8") + "\nstale\n",
        encoding="utf-8",
    )

    exit_code = main(["list", "--json"], repo_root=metadata_root)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert "stale" in payload["error"]
    assert captured.err == ""
    assert str(metadata_root.resolve()) not in captured.out
