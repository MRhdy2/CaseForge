"""
发现并加载技能模块，包括解析 skill.yaml 和导入 handler.py。
loader.py 负责扫描 skills 目录下的含有skill.yaml的子目录，读取每个技能的元数据，并动态导入其处理函数。

"""

import importlib.util
from pathlib import Path
from typing import Any

import yaml

from app.skills.base import SkillContext, SkillMeta, SkillRunFn, SkillUIConfig

SKILLS_ROOT = Path(__file__).resolve().parent


def _parse_ui(raw: dict | None) -> SkillUIConfig:
    """
    将skill.yaml中的UI配置解析为SkillUIConfig对象。
    raw: 原始UI配置字典，可能包含selectable、group和icon字段。
    """
    raw = raw or {}
    return SkillUIConfig(
        selectable=bool(raw.get("selectable", False)),
        group=raw.get("group"),
        icon=raw.get("icon"),
    )


def _load_manifest(skill_dir: Path) -> SkillMeta:
    """
    读取技能目录下的 skill.yaml 文件，并解析为 SkillMeta 对象。
    skill_dir: 技能目录路径，必须包含 skill.yaml 文件。
    """
    manifest_path = skill_dir / "skill.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"缺少 skill.yaml: {skill_dir}")

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("name"):
        raise ValueError(f"无效的 skill.yaml: {manifest_path}")

    return SkillMeta(
        name=data["name"],
        version=str(data.get("version", "1.0.0")),
        title=data.get("title", data["name"]),
        description=data.get("description", ""),
        category=data.get("category", "utility"),
        stage=data.get("stage", "generation"),
        tags=list(data.get("tags") or []),
        ui=_parse_ui(data.get("ui")),
        inputs=dict(data.get("inputs") or {}),
        outputs=dict(data.get("outputs") or {}),
        directory=skill_dir,
        strategies=dict(data.get("strategies") or {}),
    )


def _load_handler(skill_dir: Path, skill_name: str) -> SkillRunFn:
    """
    动态导入技能目录下的 handler.py 文件，并返回其 run 函数。
    skill_dir: 技能目录路径，必须包含 handler.py 文件。
    skill_name: 技能名称，用于生成模块名。
    """
    handler_path = skill_dir / "handler.py"
    if not handler_path.exists():
        raise FileNotFoundError(f"缺少 handler.py: {skill_dir}")

    module_name = f"skill_handler_{skill_name}"
    spec = importlib.util.spec_from_file_location(module_name, handler_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 handler: {handler_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    run_fn = getattr(module, "run", None)
    if run_fn is None or not callable(run_fn):
        raise AttributeError(f"{handler_path} 必须导出 async def run(inputs, context)")
    return run_fn


def discover_skills(root: Path | None = None) -> tuple[dict[str, SkillMeta], dict[str, SkillRunFn]]:
    """
    扫描指定目录下的技能子目录，加载每个技能的元数据和处理函数。
    root: 技能根目录，默认为 SKILLS_ROOT。
    返回一个元组，包含技能名称到 SkillMeta 的映射，以及技能名称到 SkillRunFn 的映射。
    """
    root = root or SKILLS_ROOT
    metas: dict[str, SkillMeta] = {}
    handlers: dict[str, SkillRunFn] = {}

    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("_") or child.name == "shared":
            continue
        if not (child / "skill.yaml").exists():
            continue

        meta = _load_manifest(child)
        if meta.name in metas:
            raise ValueError(f"Skill 名称重复: {meta.name}")

        handler = _load_handler(child, meta.name)
        metas[meta.name] = meta
        handlers[meta.name] = handler

    if not metas:
        raise RuntimeError("未发现任何 Skill，请检查 skills 目录")

    return metas, handlers


def normalize_inputs(meta: SkillMeta, inputs: dict[str, Any]) -> dict[str, Any]:
    """
    根据技能的输入规范，检查并填充输入参数。
    meta: 技能元数据，包含输入规范。
    inputs: 用户提供的输入参数字典。
    返回一个新的字典，包含所有必填参数和默认值。
    """
    normalized = dict(inputs)
    for key, spec in meta.inputs.items():
        if spec.get("required") and key not in normalized:
            raise ValueError(f"Skill `{meta.name}` 缺少必填参数: {key}")
        if key not in normalized and "default" in spec:
            normalized[key] = spec["default"]
    return normalized
