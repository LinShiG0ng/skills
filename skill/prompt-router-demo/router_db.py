"""
Anthropic Agent Skills - 数据库后端实现

支持从数据库加载 Skills，保持与文件系统版本的 API 兼容
"""

from pathlib import Path
import json
import sys
from typing import Dict, List, Set, Tuple, Optional

from logging_utils import log_event, log_prompt
from qwen_client import QwenClient
from db_models import get_database, SkillsDatabase
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


class DBSkill:
    """
    数据库支持的 Skill 类
    从数据库加载，而不是文件系统
    支持层级结构：一级技能可以包含二级子技能
    """

    # 子技能引用标记格式: @use:skill_name 或 [[skill:skill_name]]
    CHILD_SKILL_PATTERN = r'@use:(\w+)|(?:\[\[skill:(\w+)\]\])'

    def __init__(self, skill_data: dict, db: SkillsDatabase):
        """
        从数据库记录初始化 Skill

        Args:
            skill_data: 数据库记录字典
            db: 数据库实例
        """
        self.id = skill_data['id']
        self.name = skill_data['name']
        self.description = skill_data['description']
        self.instructions = skill_data['instructions']
        self.always_load = bool(skill_data['always_load'])
        self.enabled = bool(skill_data['enabled'])
        self.version = skill_data.get('version', '1.0.0')
        self.level = skill_data.get('level', 1)
        self.parent_skill_id = skill_data.get('parent_skill_id')
        self._db = db

        # 兼容性：metadata 字典
        self.metadata = {
            'name': self.name,
            'description': self.description
        }

        # 加载资源列表
        self._resources = None
        # 缓存子技能
        self._child_skills = None
    
    @property
    def resources(self) -> List[dict]:
        """懒加载资源列表"""
        if self._resources is None:
            self._resources = self._db.get_skill_resources(self.id)
        return self._resources
    
    def get_metadata_summary(self) -> str:
        """返回元数据摘要（Level 1）"""
        return f"- **{self.name}**: {self.description}"
    
    def get_full_content(self) -> str:
        """返回完整内容（Level 2 + Level 3 说明）"""
        content = f"## Skill: {self.name}\n\n{self.instructions}"
        
        # 添加资源说明
        if self.resources:
            content += f"\n\n### Available Resources\n\n"
            content += f"This skill has {len(self.resources)} resources available:\n\n"
            
            for resource in self.resources:
                res_type = resource['resource_type']
                res_name = resource['resource_name']
                res_desc = resource.get('description', '')
                content += f"- `{res_name}` [{res_type}]: {res_desc}\n"
        
        return content
    
    def get_resource(self, resource_name: str) -> Optional[str]:
        """获取资源内容（Level 3）"""
        return self._db.get_resource_content(self.id, resource_name)
    
    def list_resources(self) -> List[str]:
        """列出所有资源名称"""
        return [r['resource_name'] for r in self.resources]

    @property
    def child_skills(self) -> List[dict]:
        """懒加载子技能列表"""
        if self._child_skills is None:
            self._child_skills = self._db.get_child_skills(self.id)
        return self._child_skills

    def get_referenced_child_skills(self) -> List[str]:
        """
        解析 instructions 中引用的子技能名称
        支持格式: @use:skill_name 或 [[skill:skill_name]]
        """
        import re
        pattern = self.CHILD_SKILL_PATTERN
        matches = re.findall(pattern, self.instructions)
        # matches 是元组列表，每个元组包含两个捕获组
        referenced = []
        for match in matches:
            # match[0] 是 @use:skill_name 格式
            # match[1] 是 [[skill:skill_name]] 格式
            skill_name = match[0] or match[1]
            if skill_name and skill_name not in referenced:
                referenced.append(skill_name)
        return referenced

    def is_top_level(self) -> bool:
        """判断是否为一级技能"""
        return self.level == 1


class DBSkillManager:
    """
    数据库支持的 SkillManager
    使用数据库作为 Skills 的存储后端
    支持层级化技能结构：一级技能可见，二级技能嵌套加载
    """

    def __init__(self, db: SkillsDatabase = None):
        self.db = db or get_database()
        self.skills: Dict[str, DBSkill] = {}  # 所有技能（包括一级和二级）
        self.top_level_skills: Dict[str, DBSkill] = {}  # 仅一级技能
        self.sessions: Dict[str, dict] = {}
        self._load_skills()

    def _load_skills(self):
        """从数据库加载所有 Skills 的元数据"""
        logger.info("=" * 60)
        logger.info("DBSkillManager 初始化（数据库后端 - 层级化支持）")
        logger.info("=" * 60)

        skill_records = self.db.get_all_skills(enabled_only=True)

        level_1_count = 0
        level_2_count = 0

        for record in skill_records:
            skill = DBSkill(record, self.db)
            self.skills[skill.name] = skill

            # 仅一级技能加入 top_level_skills
            if skill.level == 1:
                self.top_level_skills[skill.name] = skill
                level_1_count += 1
            else:
                level_2_count += 1

            logger.info(f"加载 Skill: {skill.name}")
            logger.info(f"  - ID: {skill.id}")
            logger.info(f"  - Level: {skill.level}")
            logger.info(f"  - Parent: {skill.parent_skill_id or 'None'}")
            logger.info(f"  - Always Load: {skill.always_load}")
            logger.info(f"  - Version: {skill.version}")
            logger.info(f"  - Description: {skill.description[:60]}...")

        print(f"\n[DBSkillManager] Loaded {len(self.skills)} skills from database")
        print(f"  - Level 1 (Top-level): {level_1_count}")
        print(f"  - Level 2 (Child): {level_2_count}")

        always_load_skills = [s.name for s in self.top_level_skills.values() if s.always_load]
        optional_skills = [s.name for s in self.top_level_skills.values() if not s.always_load]
        print(f"  - Always Load: {', '.join(always_load_skills) or 'None'}")
        print(f"  - On-Demand: {', '.join(optional_skills) or 'None'}")

        logger.info("=" * 60)
    
    def reload_skills(self):
        """重新加载所有 Skills（热更新）"""
        self.skills.clear()
        self.top_level_skills.clear()
        self._load_skills()
        print("[DBSkillManager] Skills reloaded")
    
    def get_skill_resource(self, skill_name: str, resource_name: str) -> Optional[str]:
        """获取资源内容"""
        if skill_name not in self.skills:
            return None
        return self.skills[skill_name].get_resource(resource_name)
    
    def list_skill_resources(self, skill_name: str) -> List[str]:
        """列出资源"""
        if skill_name not in self.skills:
            return []
        return self.skills[skill_name].list_resources()
    
    def get_all_metadata_summary(self) -> str:
        """
        生成所有一级技能的元数据摘要（Level 1）
        注意：只展示一级技能，二级技能的描述不会出现在初始摘要中
        """
        lines = ["# Available Skills\n"]
        lines.append("The following skills are available for activation based on task requirements:\n")

        # 始终加载的一级 skills
        always_load = [s for s in self.top_level_skills.values() if s.always_load]
        if always_load:
            lines.append("## Core Skills (Always Active)")
            for skill in always_load:
                lines.append(skill.get_metadata_summary())
            lines.append("")

        # 可选的一级 skills
        optional = [s for s in self.top_level_skills.values() if not s.always_load]
        if optional:
            lines.append("## Specialized Skills (Activated On-Demand)")
            for skill in optional:
                lines.append(skill.get_metadata_summary())

        return "\n".join(lines)
    
    def determine_needed_skills(self, question: str, loaded_skills: Set[str]) -> List[str]:
        """
        AI 判断需要哪些一级技能
        注意：只判断一级技能，二级技能通过嵌套引用加载
        """
        needed = []

        # 始终加载的一级 skills
        for skill_name, skill in self.top_level_skills.items():
            if skill.always_load:
                needed.append(skill_name)

        # 检查未加载的 optional 一级 skills
        optional_skills = {
            name: skill for name, skill in self.top_level_skills.items()
            if not skill.always_load and name not in loaded_skills
        }

        if not optional_skills:
            logger.info("[AI判断] 所有 optional 一级 skills 已加载，跳过判断")
            return needed

        # 使用 AI 判断
        logger.info("[AI判断] 正在分析问题，判断需要哪些一级 skills...")
        ai_selected = self._ai_judge_skills(question, optional_skills)

        if ai_selected:
            needed.extend(ai_selected)
            logger.info(f"[AI判断] AI 决定加载: {', '.join(ai_selected)}")
        else:
            logger.info("[AI判断] AI 认为不需要额外的 optional skills")

        return needed

    def get_child_skills_for_parent(self, parent_skill: DBSkill) -> List[DBSkill]:
        """
        获取父技能引用的所有子技能
        解析 instructions 中的 @use:skill_name 或 [[skill:skill_name]] 标记
        """
        referenced_names = parent_skill.get_referenced_child_skills()
        child_skills = []

        for name in referenced_names:
            if name in self.skills:
                child = self.skills[name]
                # 确认这个技能确实是子技能（level > 1）
                if child.level > 1:
                    child_skills.append(child)
                    logger.info(f"[嵌套加载] 发现子技能引用: {parent_skill.name} -> {name}")

        return child_skills
    
    def _ai_judge_skills(self, question: str, optional_skills: Dict[str, DBSkill]) -> List[str]:
        """使用 AI 判断需要哪些 skills"""
        skills_info = []
        for name, skill in optional_skills.items():
            skills_info.append(f"- {name}: {skill.description}")
        
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
            
            selected_skills = []
            for skill_name in optional_skills.keys():
                if skill_name.lower() in response_lower:
                    selected_skills.append(skill_name)
            
            return selected_skills
            
        except Exception as e:
            logger.error(f"[AI判断] AI 判断失败: {e}")
            return []
    
    def build_prompt_progressive(
        self,
        question: str,
        session_id: str
    ) -> Tuple[str, List[str], Set[str]]:
        """
        渐进披露：构建 prompt
        支持层级化技能：
        1. 只在元数据摘要中展示一级技能
        2. 当一级技能被加载时，解析其 instructions 中的子技能引用并加载
        """

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "loaded_skills": set(),
                "loaded_child_skills": set(),  # 追踪已加载的子技能
                "history": []
            }

        session = self.sessions[session_id]
        loaded_skills = session["loaded_skills"]
        loaded_child_skills = session.get("loaded_child_skills", set())

        # 判断需要的一级技能
        needed_skills = self.determine_needed_skills(question, loaded_skills)

        needed_set = set(needed_skills)
        newly_loaded = needed_set - loaded_skills

        # 收集需要加载的子技能
        child_skills_to_load = []
        for skill_name in needed_set:
            if skill_name in self.skills:
                skill = self.skills[skill_name]
                children = self.get_child_skills_for_parent(skill)
                for child in children:
                    if child.name not in loaded_child_skills:
                        child_skills_to_load.append(child)

        logger.info(f"\n{'='*60}")
        logger.info(f"Session: {session_id}")
        logger.info(f"Question: {question[:100]}...")
        logger.info(f"{'='*60}")
        logger.info(f"已加载一级 Skills: {', '.join(sorted(loaded_skills)) if loaded_skills else 'None'}")
        logger.info(f"需要的一级 Skills: {', '.join(needed_skills)}")
        logger.info(f"新加载一级 Skills: {', '.join(sorted(newly_loaded)) if newly_loaded else 'None'}")
        if child_skills_to_load:
            logger.info(f"嵌套加载子 Skills: {', '.join(s.name for s in child_skills_to_load)}")

        prompt_parts = []

        # Level 1: 元数据摘要（只包含一级技能）
        metadata_summary = self.get_all_metadata_summary()
        prompt_parts.append(metadata_summary)
        prompt_parts.append("\n" + "=" * 60 + "\n")

        # Level 2: 完整内容 - 包含所有需要的一级技能
        all_skills_for_prompt = []

        if needed_skills:
            logger.info(f"\n[Level 2] 注入一级技能完整内容")
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

        # Level 2.5: 嵌套加载的子技能
        if child_skills_to_load:
            logger.info(f"\n[Level 2.5] 注入嵌套子技能完整内容")
            prompt_parts.append("\n# Child Skills (Nested Loading)\n")
            prompt_parts.append("The following child skills are loaded based on parent skill references:\n")

            newly_loaded_children = set()
            for child in child_skills_to_load:
                content = child.get_full_content()
                prompt_parts.append(content)
                prompt_parts.append("\n" + "-" * 60 + "\n")
                all_skills_for_prompt.append(child.name)
                newly_loaded_children.add(child.name)
                logger.info(f"  - {child.name}: {len(content)} chars (Level {child.level}, Child of ID:{child.parent_skill_id})")

            session["loaded_child_skills"] = loaded_child_skills.union(newly_loaded_children)

            if newly_loaded_children:
                print(f"[Progressive] NESTED: Loaded {len(newly_loaded_children)} child skills: {', '.join(sorted(newly_loaded_children))}")

        if newly_loaded:
            print(f"[Progressive] NEW: Loaded {len(newly_loaded)} skills: {', '.join(sorted(newly_loaded))}")
        elif needed_skills:
            print(f"[Progressive] REUSE: Using loaded skills: {', '.join(sorted(needed_set))}")

        full_prompt = "".join(prompt_parts)

        return full_prompt, all_skills_for_prompt, newly_loaded
    
    def add_to_history(self, session_id: str, question: str, answer: str):
        """保存对话到历史"""
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
        """获取会话历史"""
        if session_id not in self.sessions:
            return []
        return self.sessions[session_id]["history"]
    
    def clear_session(self, session_id: str):
        """清除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"[DBSkillManager] Session {session_id} cleared")
    
    def get_skill_metadata_list(self) -> List[dict]:
        """获取所有 skills 的元数据列表（包含层级信息）"""
        return [
            {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "always_load": skill.always_load,
                "enabled": skill.enabled,
                "version": skill.version,
                "level": skill.level,
                "parent_skill_id": skill.parent_skill_id,
                "resources_count": len(skill.resources)
            }
            for skill in self.skills.values()
        ]

    def get_top_level_skill_list(self) -> List[dict]:
        """获取所有一级 skills 的元数据列表"""
        return [
            {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "always_load": skill.always_load,
                "enabled": skill.enabled,
                "version": skill.version,
                "level": skill.level,
                "resources_count": len(skill.resources),
                "child_count": len(skill.child_skills)
            }
            for skill in self.top_level_skills.values()
        ]


# ==================== 兼容层 ====================

# 全局实例
_db_skill_manager: Optional[DBSkillManager] = None


def get_skill_manager() -> DBSkillManager:
    """获取全局 DBSkillManager 实例"""
    global _db_skill_manager
    if _db_skill_manager is None:
        _db_skill_manager = DBSkillManager()
    return _db_skill_manager


def build_messages_with_history(
    prompt: str, 
    question: str, 
    history: List[dict]
) -> List[dict]:
    """构建包含历史的消息列表"""
    messages = [{"role": "system", "content": prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages


def answer(question: str, session_id: str = "default") -> dict:
    """处理用户问题"""
    manager = get_skill_manager()
    client = QwenClient()
    
    prompt, skills, newly_loaded = manager.build_prompt_progressive(question, session_id)
    history = manager.get_history(session_id)
    messages = build_messages_with_history(prompt, question, history)
    
    print(f"\n{'='*60}")
    print(f"[Question] {question}")
    print(f"[Session] {session_id}")
    print(f"[Involved Skills] {', '.join(skills)}")
    if newly_loaded:
        print(f"[Newly Loaded] NEW: {', '.join(sorted(newly_loaded))}")
    else:
        print(f"[Newly Loaded] REUSE: None (reusing loaded skills)")
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
    
    log_event(
        "chat",
        {
            "session_id": session_id,
            "question": question,
            "skills": skills,
            "newly_loaded_skills": list(newly_loaded),
            "prompt_length": len(prompt),
            "answer_length": len(output),
            "answer": output,
            "storage_backend": "database"
        },
    )
    
    return {
        "session_id": session_id,
        "skills": skills,
        "newly_loaded_skills": list(newly_loaded),
        "answer": output
    }


def main() -> int:
    """命令行入口"""
    if len(sys.argv) < 2:
        print("Usage: python router_db.py \"<question>\" [session_id]")
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

