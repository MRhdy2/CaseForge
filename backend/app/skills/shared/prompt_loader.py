"""
    作用：加载技能相关的提示文件,Markdown格式的提示文件
    何时使用：当需要加载特定技能的提示内容时使用
"""
from pathlib import Path


def load_prompt(skill_dir: Path, relative_path: str) -> str:
    path = skill_dir / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {path}")
    return path.read_text(encoding="utf-8").strip()
