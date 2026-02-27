"""
Anthropic Agent Skills - 文件系统后端实现

从本地文件读取 Skills（快速），数据库仅作镜像备份。
目录结构:
  skills/L1/  - 一级技能（AI 可直接加载）
  skills/L2/  - 二级技能（通过 @use:skill_name 引用加载）

文件格式 (YAML frontmatter + Markdown):
  ---
  name: skill_name
  description: Short description
  always_load: false
  version: 1.0.0
  ---
  # Instructions
  Full content here...
  @use:other_skill_name
"""

from pathlib import Path
import re
import sys
from typing import Dict, List, Set, Tuple, Optional

from logging_utils import log_event, log_prompt
from qwen_client import QwenClient
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
SKILLS_DIR = BASE_DIR / "skills"
L1_DIR = SKILLS_DIR / "L1"
L2_DIR = SKILLS_DIR / "L2"

# 子技能引用标记: @use:skill_name 或 [[skill:skill_name]]
CHILD_SKILL_PATTERN = r'@use:(\w+)|(?:\[\[skill:(\w+)\]\])'


def _parse_skill_file(path: Path, level: int) -> Optional[dict]:
    """
    解析技能 .md 文件，提取 frontmatter 和 instructions。
    返回技能数据字典，解析失败返回 None。
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"读取文件失败 {path}: {e}")
        return None

    # 解析 YAML frontmatter
    frontmatter = {}
    instructions = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            import yaml
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except Exception:
                frontmatter = {}
            instructions = parts[2].strip()

    # name 优先从 frontmatter 取，否则用文件名
    name = frontmatter.get("name") or path.stem

    return {
        "name": name,
        "description": frontmatter.get("description", ""),
        "always_load": bool(frontmatter.get("always_load", False)),
        "enabled": bool(frontmatter.get("enabled", True)),
        "version": frontmatter.get("version", "1.0.0"),
        "level": level,
        "instructions": instructions,
        "file_path": str(path),
    }


def _write_skill_file(level: int, name: str, description: str,
                      instructions: str, always_load: bool,
                      version: str = "1.0.0", enabled: bool = True) -> Path:
    """将技能写入对应层级的 .md 文件，返回文件路径。"""
    directory = L1_DIR if level == 1 else L2_DIR
    directory.mkdir(parents=True, exist_ok=True)

    # 使用技能名作为文件名（替换空格为下划线）
    filename = re.sub(r'[^\w\-]', '_', name) + ".md"
    path = directory / filename

    content = f"""---
name: {name}
description: {description}
always_load: {"true" if always_load else "false"}
enabled: {"true" if enabled else "false"}
version: {version}
---

{instructions}
"""
    path.write_text(content, encoding="utf-8")
    logger.info(f"[FileSkill] 写入文件: {path}")
    return path


def _delete_skill_file(level: int, name: str) -> bool:
    """删除技能文件，返回是否成功。"""
    directory = L1_DIR if level == 1 else L2_DIR
    filename = re.sub(r'[^\w\-]', '_', name) + ".md"
    path = directory / filename

    if path.exists():
        path.unlink()
        logger.info(f"[FileSkill] 删除文件: {path}")
        return True

    # 找不到精确文件时，扫描目录查找匹配的 name
    for f in directory.glob("*.md"):
        data = _parse_skill_file(f, level)
        if data and data["name"] == name:
            f.unlink()
            logger.info(f"[FileSkill] 删除文件: {f}")
            return True

    return False


class FileSkill:
    """
    文件系统支持的 Skill 类。
    从 .md 文件加载，支持层级结构。
    """

    def __init__(self, data: dict):
        self.name = data["name"]
        self.description = data["description"]
        self.instructions = data["instructions"]
        self.always_load = data["always_load"]
        self.enabled = data["enabled"]
        self.version = data["version"]
        self.level = data["level"]
        self.file_path = data.get("file_path", "")

        # 数据库 ID（同步后填入，供 API 返回）
        self.id: Optional[int] = data.get("id")
        self.parent_skill_id: Optional[int] = data.get("parent_skill_id")

        self.metadata = {"name": self.name, "description": self.description}

    def get_metadata_summary(self) -> str:
        return f"- **{self.name}**: {self.description}"

    def get_full_content(self) -> str:
        return f"## Skill: {self.name}\n\n{self.instructions}"

    def get_referenced_child_skills(self) -> List[str]:
        """解析 instructions 中引用的技能名称。"""
        matches = re.findall(CHILD_SKILL_PATTERN, self.instructions)
        referenced = []
        for match in matches:
            skill_name = match[0] or match[1]
            if skill_name and skill_name not in referenced:
                referenced.append(skill_name)
        return referenced

    def is_top_level(self) -> bool:
        return self.level == 1


class FileSkillManager:
    """
    文件系统后端的 SkillManager。
    启动时扫描 skills/L1/ 和 skills/L2/ 目录加载所有技能，
    运行期间不再访问数据库。
    """

    def __init__(self):
        self.skills: Dict[str, FileSkill] = {}
        self.top_level_skills: Dict[str, FileSkill] = {}
        self.sessions: Dict[str, dict] = {}
        self._load_skills()

    def _load_skills(self):
        """扫描 L1/ 和 L2/ 目录加载所有技能文件。"""
        logger.info("=" * 60)
        logger.info("FileSkillManager 初始化（文件系统后端）")
        logger.info(f"L1 目录: {L1_DIR}")
        logger.info(f"L2 目录: {L2_DIR}")
        logger.info("=" * 60)

        self.skills.clear()
        self.top_level_skills.clear()

        level_1_count = 0
        level_2_count = 0

        for level, directory in [(1, L1_DIR), (2, L2_DIR)]:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                continue

            for path in sorted(directory.glob("*.md")):
                data = _parse_skill_file(path, level)
                if not data:
                    continue
                if not data["enabled"]:
                    logger.info(f"跳过禁用 Skill: {data['name']}")
                    continue

                skill = FileSkill(data)
                self.skills[skill.name] = skill

                if level == 1:
                    self.top_level_skills[skill.name] = skill
                    level_1_count += 1
                else:
                    level_2_count += 1

                logger.info(f"加载 Skill: {skill.name} (Level {level}, always_load={skill.always_load})")

        print(f"\n[FileSkillManager] Loaded {len(self.skills)} skills from files")
        print(f"  - Level 1 (Top-level): {level_1_count}")
        print(f"  - Level 2 (Child): {level_2_count}")

        always_load = [s.name for s in self.top_level_skills.values() if s.always_load]
        optional = [s.name for s in self.top_level_skills.values() if not s.always_load]
        print(f"  - Always Load: {', '.join(always_load) or 'None'}")
        print(f"  - On-Demand:   {', '.join(optional) or 'None'}")
        logger.info("=" * 60)

    def reload_skills(self):
        """重新扫描文件目录（热更新）。"""
        self._load_skills()
        print("[FileSkillManager] Skills reloaded from files")

    # ------------------------------------------------------------------ #
    #  公共查询接口                                                         #
    # ------------------------------------------------------------------ #

    def get_skill_metadata_list(self) -> List[dict]:
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "always_load": s.always_load,
                "enabled": s.enabled,
                "version": s.version,
                "level": s.level,
                "parent_skill_id": s.parent_skill_id,
                "resources_count": 0,
            }
            for s in self.skills.values()
        ]

    def get_top_level_skill_list(self) -> List[dict]:
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "always_load": s.always_load,
                "enabled": s.enabled,
                "version": s.version,
                "level": s.level,
                "resources_count": 0,
                "child_count": len([
                    x for x in self.skills.values()
                    if x.level == 2 and x.parent_skill_id == s.id
                ]),
            }
            for s in self.top_level_skills.values()
        ]

    # ------------------------------------------------------------------ #
    #  Prompt 构建                                                         #
    # ------------------------------------------------------------------ #

    def get_all_metadata_summary(self) -> str:
        lines = ["# Available Skills\n"]
        lines.append("The following skills are available for activation based on task requirements:\n")

        always_load = [s for s in self.top_level_skills.values() if s.always_load]
        if always_load:
            lines.append("## Core Skills (Always Active)")
            for s in always_load:
                lines.append(s.get_metadata_summary())
            lines.append("")

        optional = [s for s in self.top_level_skills.values() if not s.always_load]
        if optional:
            lines.append("## Specialized Skills (Activated On-Demand)")
            for s in optional:
                lines.append(s.get_metadata_summary())

        return "\n".join(lines)

    def determine_needed_skills(self, question: str, loaded_skills: Set[str]) -> List[str]:
        needed = []

        for name, skill in self.top_level_skills.items():
            if skill.always_load:
                needed.append(name)

        optional_skills = {
            name: skill for name, skill in self.top_level_skills.items()
            if not skill.always_load and name not in loaded_skills
        }

        if not optional_skills:
            return needed

        logger.info("[AI判断] 正在分析问题，判断需要哪些一级 skills...")
        ai_selected = self._ai_judge_skills(question, optional_skills)
        if ai_selected:
            needed.extend(ai_selected)
            logger.info(f"[AI判断] AI 决定加载: {', '.join(ai_selected)}")
        else:
            logger.info("[AI判断] AI 认为不需要额外的 optional skills")

        return needed

    def get_all_referenced_skills_recursive(
        self,
        skill: FileSkill,
        already_collected: Set[str] = None
    ) -> List[FileSkill]:
        """递归获取技能引用的所有技能（支持任意深度）。"""
        if already_collected is None:
            already_collected = set()

        result = []
        for name in skill.get_referenced_child_skills():
            if name in already_collected:
                continue
            if name in self.skills:
                ref = self.skills[name]
                already_collected.add(name)
                result.append(ref)
                logger.info(f"[递归加载] {skill.name} -> {name} (Level {ref.level})")
                result.extend(self.get_all_referenced_skills_recursive(ref, already_collected))

        return result

    def build_prompt_progressive(
        self,
        question: str,
        session_id: str
    ) -> Tuple[str, List[str], Set[str]]:
        """渐进披露：构建 prompt（完全从内存/文件，无 DB 访问）。"""

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "loaded_skills": set(),
                "loaded_child_skills": set(),
                "history": []
            }

        session = self.sessions[session_id]
        loaded_skills = session["loaded_skills"]
        loaded_child_skills = session["loaded_child_skills"]

        # 判断需要的一级技能
        needed_skills = self.determine_needed_skills(question, loaded_skills)
        needed_set = set(needed_skills)
        newly_loaded = needed_set - loaded_skills

        # 递归收集引用的二级技能
        child_skills_to_load: List[FileSkill] = []
        already_collected = set(loaded_child_skills)
        for skill_name in needed_set:
            if skill_name in self.skills:
                refs = self.get_all_referenced_skills_recursive(
                    self.skills[skill_name], already_collected.copy()
                )
                for ref in refs:
                    if ref.name not in loaded_child_skills and ref.name not in [s.name for s in child_skills_to_load]:
                        child_skills_to_load.append(ref)
                        already_collected.add(ref.name)

        logger.info(f"\n{'='*60}")
        logger.info(f"Session: {session_id}")
        logger.info(f"需要的一级 Skills: {', '.join(needed_skills)}")
        logger.info(f"新加载一级 Skills: {', '.join(sorted(newly_loaded)) if newly_loaded else 'None'}")
        if child_skills_to_load:
            logger.info(f"递归加载引用 Skills: {', '.join(s.name for s in child_skills_to_load)}")

        prompt_parts = []

        # Level 1: 元数据摘要
        prompt_parts.append(self.get_all_metadata_summary())
        prompt_parts.append("\n" + "=" * 60 + "\n")

        all_skills_for_prompt = []

        # Level 2: 一级技能完整内容
        if needed_skills:
            prompt_parts.append("# Activated Skills\n")
            prompt_parts.append("The following skills have been activated for this session:\n")
            for skill_name in sorted(needed_set):
                skill = self.skills[skill_name]
                content = skill.get_full_content()
                prompt_parts.append(content)
                prompt_parts.append("\n" + "-" * 60 + "\n")
                all_skills_for_prompt.append(skill_name)
                logger.info(f"  - {skill_name}: {len(content)} chars (Level 1)")
            session["loaded_skills"].update(newly_loaded)

        # Level 2.5: 递归引用的技能
        if child_skills_to_load:
            prompt_parts.append("\n# Referenced Skills (Recursive Loading)\n")
            prompt_parts.append("The following skills are loaded based on @use:skill_name references:\n")
            newly_loaded_children = set()
            for child in child_skills_to_load:
                content = child.get_full_content()
                prompt_parts.append(content)
                prompt_parts.append("\n" + "-" * 60 + "\n")
                all_skills_for_prompt.append(child.name)
                newly_loaded_children.add(child.name)
                logger.info(f"  - {child.name}: {len(content)} chars (Level {child.level})")
            session["loaded_child_skills"] = loaded_child_skills.union(newly_loaded_children)
            if newly_loaded_children:
                print(f"[Progressive] RECURSIVE: Loaded {len(newly_loaded_children)} referenced skills: "
                      f"{', '.join(sorted(newly_loaded_children))}")

        if newly_loaded:
            print(f"[Progressive] NEW: Loaded {len(newly_loaded)} skills: {', '.join(sorted(newly_loaded))}")
        elif needed_skills:
            print(f"[Progressive] REUSE: Using loaded skills: {', '.join(sorted(needed_set))}")

        return "".join(prompt_parts), all_skills_for_prompt, newly_loaded

    # ------------------------------------------------------------------ #
    #  Session 管理                                                        #
    # ------------------------------------------------------------------ #

    def add_to_history(self, session_id: str, question: str, answer: str):
        if session_id not in self.sessions:
            return
        session = self.sessions[session_id]
        session["history"].extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ])
        if len(session["history"]) > 20:
            session["history"] = session["history"][-20:]

    def get_history(self, session_id: str) -> List[dict]:
        if session_id not in self.sessions:
            return []
        return self.sessions[session_id]["history"]

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"[FileSkillManager] Session {session_id} cleared")

    # ------------------------------------------------------------------ #
    #  内部 AI 判断                                                        #
    # ------------------------------------------------------------------ #

    def _ai_judge_skills(self, question: str, optional_skills: Dict[str, FileSkill]) -> List[str]:
        skills_info = [f"- {name}: {skill.description}" for name, skill in optional_skills.items()]
        judge_prompt = f"""You are analyzing a user's question to determine which specialized skills are needed.

Available specialized skills (optional):
{chr(10).join(skills_info)}

User's question: {question}

Based on the question's intent and requirements, which skills (if any) are needed?

Reply ONLY with skill names separated by commas (e.g., "capabilities, tools, planning").
If no optional skills are needed, reply with "none".

Your answer:"""

        try:
            client = QwenClient()
            response = client.chat([{"role": "user", "content": judge_prompt}])
            logger.info(f"[AI判断] AI 原始回复: {response}")
            response_lower = response.strip().lower()
            if response_lower == "none" or not response_lower:
                return []
            return [name for name in optional_skills if name.lower() in response_lower]
        except Exception as e:
            logger.error(f"[AI判断] 失败: {e}")
            return []


# ------------------------------------------------------------------ #
#  全局实例 & 兼容接口                                                  #
# ------------------------------------------------------------------ #

_file_skill_manager: Optional[FileSkillManager] = None


def get_skill_manager() -> FileSkillManager:
    global _file_skill_manager
    if _file_skill_manager is None:
        _file_skill_manager = FileSkillManager()
    return _file_skill_manager


def build_messages_with_history(prompt: str, question: str, history: List[dict]) -> List[dict]:
    messages = [{"role": "system", "content": prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages


def answer(question: str, session_id: str = "default") -> dict:
    manager = get_skill_manager()
    client = QwenClient()

    prompt, skills, newly_loaded = manager.build_prompt_progressive(question, session_id)
    history = manager.get_history(session_id)
    messages = build_messages_with_history(prompt, question, history)

    print(f"\n{'='*60}")
    print(f"[Question] {question}")
    print(f"[Session] {session_id}")
    print(f"[Involved Skills] {', '.join(skills)}")
    print(f"[Newly Loaded] {'NEW: ' + ', '.join(sorted(newly_loaded)) if newly_loaded else 'REUSE'}")
    print(f"[Prompt Length] {len(prompt)} chars (~{len(prompt) // 4} tokens)")
    print(f"{'='*60}\n")

    log_prompt(
        session_id=session_id,
        question=question,
        prompt=prompt,
        messages=messages,
        metadata={
            "skills": skills,
            "newly_loaded": list(newly_loaded),
            "history": history,
            "prompt_length": len(prompt),
            "estimated_tokens": len(prompt) // 4
        }
    )

    output = client.chat(messages)
    print(f"[Answer] {output[:100]}...")

    manager.add_to_history(session_id, question, output)

    log_event("chat", {
        "session_id": session_id,
        "question": question,
        "skills": skills,
        "newly_loaded_skills": list(newly_loaded),
        "prompt_length": len(prompt),
        "answer_length": len(output),
        "answer": output,
        "storage_backend": "file"
    })

    return {
        "session_id": session_id,
        "skills": skills,
        "newly_loaded_skills": list(newly_loaded),
        "answer": output
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python router_file.py \"<question>\" [session_id]")
        return 1
    question = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else "default"
    result = answer(question, session_id)
    print(f"\n{'='*60}")
    print(f"[Session] {result['session_id']}")
    print(f"[Skills] {', '.join(result['skills'])}")
    print(f"{'='*60}")
    print(f"\n{result['answer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
