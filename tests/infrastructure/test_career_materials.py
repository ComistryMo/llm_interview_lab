from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

import llm_interview_lab.materials as materials_module
import llm_interview_lab.workspace as workspace_module
from llm_interview_lab.materials import (
    MAX_MATERIAL_BYTES,
    MaterialError,
    add_material,
    get_material,
    list_materials,
    resolve_material_path,
)
from llm_interview_lab.workspace import WorkspaceError, init_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _workspace_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n",
        encoding="utf-8",
    )
    shutil.copytree(REPO_ROOT / "workspace" / "schema", root / "workspace" / "schema")
    shutil.copytree(
        REPO_ROOT / "workspace" / "templates",
        root / "workspace" / "templates",
    )
    profiles = root / "workspace" / "profiles"
    profiles.mkdir()
    (profiles / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _text_source(tmp_path: Path, name: str = "resume.md") -> Path:
    source = tmp_path / name
    source.write_text("# Sanitized resume\n\nPython and PyTorch.\n", encoding="utf-8")
    return source


def test_init_adds_career_directories_and_upgrades_old_profile_without_rewriting_facts(
    tmp_path: Path,
) -> None:
    root = _workspace_repo(tmp_path)
    first = init_profile(root, "learner-one")
    paths = first.paths
    assert paths.materials_root.is_dir()
    assert paths.interviews_root.is_dir()

    paths.materials_root.rmdir()
    paths.interviews_root.rmdir()
    profile_before = paths.profile_file.read_bytes()
    events_before = paths.events_file.read_bytes()

    second = init_profile(root, "learner-one")

    assert not second.created
    assert paths.materials_root.is_dir()
    assert paths.interviews_root.is_dir()
    assert paths.profile_file.read_bytes() == profile_before
    assert paths.events_file.read_bytes() == events_before


def test_material_commands_lazily_upgrade_an_existing_profile(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    paths.materials_root.rmdir()
    profile_before = paths.profile_file.read_bytes()
    events_before = paths.events_file.read_bytes()

    assert list_materials(root, "learner-one") == ()
    added = add_material(
        root,
        "learner-one",
        _text_source(tmp_path),
        material_id="resume-main",
        kind="resume",
        ai_access=True,
    )

    assert paths.materials_root.is_dir()
    assert get_material(root, "learner-one", added.id) == added
    assert paths.profile_file.read_bytes() == profile_before
    assert paths.events_file.read_bytes() == events_before


def test_add_list_get_store_one_profile_relative_manifest_without_source_path(
    tmp_path: Path,
) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    source = _text_source(tmp_path)

    added = add_material(
        root,
        "learner-one",
        source,
        material_id="resume-main",
        kind="resume",
        title="Public resume",
        tags=("llm", "python"),
        ai_access=True,
    )

    assert added.id == "resume-main"
    assert not added.opaque
    assert added.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert list_materials(root, "learner-one") == (added,)
    assert get_material(root, "learner-one", "resume-main") == added
    stored = resolve_material_path(root, "learner-one", added)
    assert stored.read_bytes() == source.read_bytes()
    assert stored == paths.root / "materials/files/resume-main.md"

    manifest = json.loads((paths.materials_root / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"schema_version", "materials"}
    assert set(manifest["materials"][0]) == {
        "id",
        "kind",
        "relative_path",
        "sha256",
        "size_bytes",
        "title",
        "tags",
        "ai_access",
    }
    assert manifest["materials"][0]["relative_path"] == "materials/files/resume-main.md"
    assert str(source.resolve()) not in json.dumps(manifest)
    assert not Path(manifest["materials"][0]["relative_path"]).is_absolute()


@pytest.mark.parametrize(
    "suffix,kind",
    [
        (".md", "resume"),
        (".txt", "experience"),
        (".json", "research"),
        (".yaml", "job_description"),
        (".yml", "portfolio"),
    ],
)
def test_supported_text_formats_are_utf8_and_can_be_ai_readable(
    tmp_path: Path,
    suffix: str,
    kind: str,
) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    source = tmp_path / f"material{suffix}"
    source.write_text("sanitized: true\n", encoding="utf-8")

    record = add_material(
        root,
        "learner-one",
        source,
        material_id=f"text-{suffix[1:]}",
        kind=kind,
        ai_access=True,
    )

    assert record.ai_access
    assert not record.opaque


@pytest.mark.parametrize("suffix", [".pdf", ".docx"])
def test_pdf_and_docx_are_opaque_and_cannot_enable_ai_access(
    tmp_path: Path,
    suffix: str,
) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    source = tmp_path / f"attachment{suffix}"
    source.write_bytes(b"opaque fixture")

    record = add_material(
        root,
        "learner-one",
        source,
        material_id=f"opaque-{suffix[1:]}",
        kind="research",
    )
    assert record.opaque
    assert not record.ai_access

    second = tmp_path / f"second{suffix}"
    second.write_bytes(b"another opaque fixture")
    with pytest.raises(MaterialError, match="opaque"):
        add_material(
            root,
            "learner-one",
            second,
            material_id=f"forbidden-{suffix[1:]}",
            kind="research",
            ai_access=True,
        )


def test_invalid_utf8_unsupported_type_directory_and_oversize_are_rejected(
    tmp_path: Path,
) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    invalid_utf8 = tmp_path / "invalid.txt"
    invalid_utf8.write_bytes(b"\xff\xfe")
    unsupported = tmp_path / "resume.rtf"
    unsupported.write_text("text", encoding="utf-8")
    directory = tmp_path / "folder.md"
    directory.mkdir()
    oversized = tmp_path / "large.txt"
    with oversized.open("wb") as stream:
        stream.seek(MAX_MATERIAL_BYTES)
        stream.write(b"x")

    with pytest.raises(MaterialError, match="UTF-8"):
        add_material(root, "learner-one", invalid_utf8, kind="other", ai_access=True)
    with pytest.raises(MaterialError, match="not supported"):
        add_material(root, "learner-one", unsupported, kind="other")
    with pytest.raises(MaterialError, match="regular file"):
        add_material(root, "learner-one", directory, kind="other")
    with pytest.raises(MaterialError, match="20 MiB"):
        add_material(root, "learner-one", oversized, kind="other")
    assert list_materials(root, "learner-one") == ()


def test_source_symlink_is_rejected_when_platform_can_create_it(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    target = _text_source(tmp_path)
    link = tmp_path / "linked.md"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("platform does not permit creating a test symlink")

    with pytest.raises(MaterialError, match="symlink or reparse"):
        add_material(root, "learner-one", link, kind="resume")


def test_material_ids_kinds_titles_tags_and_duplicate_ids_are_validated(
    tmp_path: Path,
) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    source = _text_source(tmp_path)

    with pytest.raises(MaterialError, match="unsupported material kind"):
        add_material(root, "learner-one", source, kind="unsupported_kind")
    with pytest.raises(MaterialError, match="material ID"):
        add_material(root, "learner-one", source, material_id="Bad_ID", kind="resume")
    with pytest.raises(MaterialError, match="title"):
        add_material(root, "learner-one", source, kind="resume", title="  ")
    with pytest.raises(MaterialError, match="unique"):
        add_material(root, "learner-one", source, kind="resume", tags=("llm", "llm"))

    add_material(root, "learner-one", source, material_id="resume-main", kind="resume")
    with pytest.raises(MaterialError, match="already exists"):
        add_material(root, "learner-one", source, material_id="resume-main", kind="resume")


def test_material_lookup_is_explicitly_profile_scoped_and_never_enumerates_peers(
    tmp_path: Path,
) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    init_profile(root, "learner-two")
    source = _text_source(tmp_path)
    one = add_material(
        root,
        "learner-one",
        source,
        material_id="resume-main",
        kind="resume",
    )

    assert list_materials(root, "learner-one") == (one,)
    assert list_materials(root, "learner-two") == ()
    with pytest.raises(MaterialError, match="unknown material ID"):
        get_material(root, "learner-two", "resume-main")
    assert not (profile_paths(root, "learner-two").materials_root / "manifest.json").exists()


def test_changed_or_missing_stored_file_is_not_silently_trusted(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    source = _text_source(tmp_path)
    record = add_material(
        root,
        "learner-one",
        source,
        material_id="resume-main",
        kind="resume",
    )
    stored = paths.root.joinpath(*record.relative_path.split("/"))
    stored.write_text("changed", encoding="utf-8")

    with pytest.raises(MaterialError, match="does not match manifest"):
        get_material(root, "learner-one", "resume-main")

    stored.unlink()
    with pytest.raises(MaterialError, match="missing"):
        list_materials(root, "learner-one")


def test_get_material_resolves_only_the_explicit_material_id(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    selected = add_material(
        root,
        "learner-one",
        _text_source(tmp_path, "selected.md"),
        material_id="selected",
        kind="resume",
    )
    unrelated = add_material(
        root,
        "learner-one",
        _text_source(tmp_path, "unrelated.md"),
        material_id="unrelated",
        kind="research",
    )
    paths.root.joinpath(*unrelated.relative_path.split("/")).write_text(
        "damaged unrelated material",
        encoding="utf-8",
    )

    assert get_material(root, "learner-one", selected.id) == selected
    with pytest.raises(MaterialError, match="unrelated|manifest"):
        list_materials(root, "learner-one")


class _ReparseStat:
    def __init__(self, original: os.stat_result) -> None:
        self.st_mode = original.st_mode
        self.st_file_attributes = 0x400


def _fake_reparse_lstat(
    monkeypatch: pytest.MonkeyPatch,
    target: Path,
) -> None:
    real_lstat = os.lstat
    expected = target.absolute()

    def fake_lstat(candidate: str | bytes | os.PathLike[str] | os.PathLike[bytes]):
        original = real_lstat(candidate)
        return _ReparseStat(original) if Path(candidate).absolute() == expected else original

    monkeypatch.setattr(materials_module.os, "lstat", fake_lstat)


@pytest.mark.parametrize("component", ["profile", "materials"])
def test_init_and_material_add_reject_reparse_profile_components_without_admin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    target = paths.root if component == "profile" else paths.materials_root
    _fake_reparse_lstat(monkeypatch, target)

    assert materials_module._is_obvious_link(target)
    assert workspace_module._is_obvious_link(target)
    with pytest.raises(WorkspaceError, match="symlink or reparse point"):
        init_profile(root, "learner-one")
    with pytest.raises(
        (MaterialError, WorkspaceError), match="symlink or reparse point"
    ):
        add_material(
            root,
            "learner-one",
            _text_source(tmp_path, f"{component}.md"),
            material_id=f"{component}-probe",
            kind="other",
        )


@pytest.mark.parametrize("component", ["profile", "materials"])
def test_init_and_material_add_reject_linked_profile_components_when_supported(
    tmp_path: Path,
    component: str,
) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    target = paths.root if component == "profile" else paths.materials_root
    outside = tmp_path / f"outside-{component}"
    if component == "profile":
        target.rename(outside)
    else:
        target.rmdir()
        outside.mkdir()
    try:
        target.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"directory symlink creation is unavailable: {error}")

    with pytest.raises(WorkspaceError, match="symlink or reparse point"):
        init_profile(root, "learner-one")
    with pytest.raises(
        (MaterialError, WorkspaceError), match="symlink or reparse point"
    ):
        add_material(
            root,
            "learner-one",
            _text_source(tmp_path, f"linked-{component}.md"),
            material_id=f"linked-{component}",
            kind="other",
        )


def test_profile_path_outside_workspace_has_distinct_error(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    outside = tmp_path / "outside-profile-path"

    with pytest.raises(WorkspaceError, match="outside workspace/profiles"):
        workspace_module.ensure_profile_path_is_safe(
            root,
            "learner-one",
            outside,
        )


def test_manifest_failure_rolls_back_new_file_and_preserves_existing_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    first_source = _text_source(tmp_path, "first.md")
    first = add_material(
        root,
        "learner-one",
        first_source,
        material_id="first",
        kind="resume",
    )
    manifest = paths.materials_root / "manifest.json"
    manifest_before = manifest.read_bytes()
    second_source = _text_source(tmp_path, "second.md")

    def fail_manifest(path: Path, value: object) -> None:
        raise OSError("injected manifest failure")

    monkeypatch.setattr(materials_module, "_atomic_write_manifest", fail_manifest)
    with pytest.raises(MaterialError, match="atomically"):
        add_material(
            root,
            "learner-one",
            second_source,
            material_id="second",
            kind="experience",
        )

    assert manifest.read_bytes() == manifest_before
    assert resolve_material_path(root, "learner-one", first).is_file()
    assert not (paths.materials_root / "files/second.md").exists()


def test_material_operations_leave_real_profile_ignored_by_git(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    source = _text_source(tmp_path)
    before = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    add_material(root, "learner-one", source, kind="resume", ai_access=True)

    after = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert after == before
