"""
    技能基础类型定义
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal

from app.services.settings_service import RuntimeModelConfig


SkillCategory = Literal["core", "specialist", "utility"]
SkillStage = Literal["requirement", "generation", "quality"]


@dataclass
class SkillUIConfig:
    """
        技能 UI 配置
    """
    selectable: bool = False
    group: str | None = None
    icon: str | None = None


@dataclass
class SkillMeta:
    """
        技能元数据
    """
    name: str
    version: str
    title: str
    description: str
    category: SkillCategory
    stage: SkillStage
    tags: list[str] = field(default_factory=list)
    ui: SkillUIConfig = field(default_factory=SkillUIConfig)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    directory: Path | None = None
    strategies: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillContext:
    """
        技能运行上下文
    """
    model_config: RuntimeModelConfig
    project_id: int | None = None
    task_id: int | None = None
    strategy: str = "detailed"
    use_mock: bool = False

#技能执行函数类型
SkillRunFn = Callable[[dict[str, Any], SkillContext], Awaitable[dict[str, Any]]]
