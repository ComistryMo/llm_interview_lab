"""Question source coverage and publishable-asset boundaries, not learner mastery."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest
import yaml

from llm_interview_lab.catalog import PROBLEM_ASSETS, load_catalog
from llm_interview_lab.role_interviews import dynamic_coding_candidates
from llm_interview_lab.roles import load_role_catalog

pytestmark = pytest.mark.infrastructure
ROOT = Path(__file__).resolve().parents[2]
NEW_IDS = ("ATT-001", "NNL-018", "NNL-019", "TNS-018", "LOSS-017", "ATT-024", "VLM-015", "ATT-023",)
SOURCE_MAPPING = (
    ("ATT-019", "ATT-004"),  # 01 MHA
    ("PT-023", "PT-015"),  # 02 GRPO Loss
    ("PT-009",),  # 03 PPO Clipped Loss
    ("PT-022",),  # 04 DPO Loss
    ("LOSS-007", "LOSS-016"),  # 05 Softmax
    ("ATT-020", "ATT-009"),  # 06 KV Cache Attention
    ("ATT-006", "ATT-020"),  # 07 GQA
    ("ATT-023",),  # 08 MLA
    ("ATT-021",),  # 09 RoPE
    ("ATT-002",),  # 10 softmax Attention
    ("ATT-019",),  # 11 Multi-Head Cross Attention
    ("LOSS-014", "PT-003"),  # 12 Cross-Entropy Loss
    ("ATT-015",),  # 13 Flash Attention
    ("LOSS-010",),  # 14 AUC Score
    ("LOSS-017", "LOSS-006"),  # 15 Contrastive Loss
    ("LOSS-004",),  # 16 KL散度
    ("NNL-006",),  # 17 LayerNorm
    ("ATT-020", "ATT-006"),  # 18 MQA as the Hkv=1 specialization
    ("NNL-008",),  # 19 RMSNorm
    ("OPT-004",),  # 20 Adam Optimizer
    ("NNL-016",),  # 21 BatchNorm
    ("ATT-022",),  # 22 Beam Search Decoding
    ("NNL-017",),  # 23 Dropout
    ("TML-004", "TML-009"),  # 24 K-Means
    ("NNL-018", "NNL-001"),  # 25 Linear Layer Backward
    ("OPT-002",),  # 26 SGD with Momentum
    ("VLM-015", "VLM-001"),  # 27 Vit Transformer Block
    ("NNL-005",),  # 28 SwiGLU MLP
    ("NNL-002",),  # 29 Embedding Layer
    ("TNS-018", "TML-008"),  # 30 余弦相似度
    ("ATT-001",),  # 31 正弦位置编码
    ("NNL-019",),  # 32 ReLU
    ("NNL-019",),  # 33 SwiGLU Activation
    ("NNL-019",),  # 34 Sigmoid
    ("TOK-001",),  # 35 BPE
    ("ATT-011",),  # 36 Top-k / Top-p Sampling
    ("ATT-024",),  # 37 GPT-2 Transformer Block
    ("NNL-014",),  # 38 MoE层
    ("INF-013",),  # 39 LoRA 低秩适配线性层
    ("PT-023",),  # 40 KL 惩罚
)


@pytest.fixture(scope="module")
def catalog():
    return load_catalog(ROOT)


def test_forty_source_topics_resolve_to_ready_validated_contracts(catalog):
    assert len(SOURCE_MAPPING) == 40
    for ids in SOURCE_MAPPING:
        assert ids
        for pid in ids:
            assert catalog.get(pid).recommendable, pid
    assert SOURCE_MAPPING[0][0] == SOURCE_MAPPING[10][0] == "ATT-019"
    assert SOURCE_MAPPING[31] == SOURCE_MAPPING[32] == SOURCE_MAPPING[33] == ("NNL-019",)


def test_new_shard_reuses_sinusoidal_id_without_duplicate_planned_node(catalog):
    shard = yaml.safe_load((ROOT / "curriculum/catalog/question_collection_coding.yaml").read_text(encoding="utf-8"))
    assert {p["id"] for p in shard["problems"]} == set(NEW_IDS)
    assert catalog.get("ATT-001").prerequisites == ("TNS-003",)
    assert all(p["id"] != "ATT-001" for p in yaml.safe_load((ROOT / "curriculum/catalog/planned_models.yaml").read_text(encoding="utf-8"))["problems"])


def test_assets_are_executable_stubs_and_only_four_public_files(catalog):
    for pid in NEW_IDS:
        p = catalog.get(pid)
        assert p.validation_level == "oracle"
        assert {f.name for f in p.problem_dir.iterdir()} == PROBLEM_ASSETS
        task = (p.problem_dir / "task.md").read_text(encoding="utf-8")
        for heading in ("## 接口", "## 题目要求", "## 共同约定", "## 口述与追问", "## 来源"):
            assert heading in task
        for file in ("starter.py", "test_public.py"):
            ast.parse((p.problem_dir / file).read_text(encoding="utf-8"), feature_version=(3, 10))
        starter = ast.parse((p.problem_dir / "starter.py").read_text(encoding="utf-8"))
        public = ast.parse(p.public_tests.read_text(encoding="utf-8"))
        functions = [n for n in starter.body if isinstance(n, ast.FunctionDef)]
        assert functions
        assert all(any(isinstance(n, ast.Raise) for n in ast.walk(fn)) for fn in functions)
        assert sum(isinstance(n, ast.FunctionDef) and n.name.startswith("test_") for n in public.body) >= 5


def test_new_hard_dependencies_can_reach_mastery(catalog):
    reachable = set()
    for pid in catalog.order:
        p = catalog.get(pid)
        if p.recommendable and set(p.prerequisites) <= reachable and all(p.retention_variant(ROOT, stage) for stage in ("d2", "d7")):
            reachable.add(pid)
    for pid in NEW_IDS:
        p = catalog.get(pid)
        assert set(p.prerequisites) <= reachable
        assert p.retention_variant(ROOT, "d2") is None
        assert p.retention_variant(ROOT, "d7") is None
    # This is a DAG reachability check; no Profile or events are read or written.


def test_architecture_and_loss_variants_are_not_silently_substituted(catalog):
    assert catalog.get("ATT-024").symbol != catalog.get("ATT-008").symbol
    assert catalog.get("VLM-015").symbol != catalog.get("VLM-001").symbol
    assert catalog.get("NNL-018").symbol != catalog.get("NNL-001").symbol
    assert catalog.get("TNS-018").symbol != catalog.get("TML-008").symbol
    assert catalog.get("LOSS-017").symbol != catalog.get("LOSS-006").symbol
    activations = ast.parse((catalog.get("NNL-019").problem_dir / "starter.py").read_text(encoding="utf-8"))
    assert {n.name for n in activations.body if isinstance(n, ast.FunctionDef)} == {"manual_relu", "stable_sigmoid", "swiglu_activation"}
    assert "sqrt(Dc+Dr)" in (catalog.get("ATT-023").problem_dir / "task.md").read_text(encoding="utf-8")


def test_existing_ontology_and_role_candidates_reach_new_contracts(catalog, monkeypatch):
    roles = load_role_catalog(ROOT, curriculum=catalog)
    for pid in NEW_IDS:
        assert set(catalog.get(pid).raw["canonical_skills"]) <= set(roles.skills)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object() if name in {"torch", "numpy"} else None)
    candidates = set()
    for role in roles.roles:
        for seniority in ("intern", "new_grad", "mid"):
            candidates.update(p.id for p, _ in dynamic_coding_candidates(catalog, roles, {"role_id":role, "seniority":seniority}))
    assert set(NEW_IDS) <= candidates
