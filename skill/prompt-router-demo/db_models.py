"""
数据库模型 - Skills 存储
MySQL 后端
"""

import json
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# MySQL 连接配置（通过环境变量或默认值）
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123.com")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "skills")


class SkillsDatabase:
    """Skills 数据库管理类 (MySQL)"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        """
        初始化 MySQL 数据库连接
        
        Args:
            host: MySQL 主机地址
            port: MySQL 端口
            user: 用户名
            password: 密码
            database: 数据库名
        """
        self.host = host or MYSQL_HOST
        self.port = port or MYSQL_PORT
        self.user = user or MYSQL_USER
        self.password = password or MYSQL_PASSWORD
        self.database = database or MYSQL_DATABASE
        
        # 用于显示的数据库路径
        self.db_path = f"mysql://{self.user}@{self.host}:{self.port}/{self.database}"
        
        # 测试连接
        self._test_connection()
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                logger.info(f"[Database] MySQL 连接成功: {self.db_path}")
        except Exception as e:
            logger.error(f"[Database] MySQL 连接失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        import pymysql
        
        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor  # 返回字典形式
        )
        try:
            yield conn
        finally:
            conn.close()
    
    # ==================== Skills CRUD ====================
    
    def create_skill(
        self,
        name: str,
        description: str,
        instructions: str,
        always_load: bool = False,
        enabled: bool = True,
        version: str = "1.0.0",
        level: int = 1,
        parent_skill_id: int = None
    ) -> int:
        """
        创建新的 Skill

        Args:
            name: 技能名称
            description: 技能描述
            instructions: 详细指令
            always_load: 是否始终加载
            enabled: 是否启用
            version: 版本号
            level: 技能级别 (1=一级技能, 2=二级技能)
            parent_skill_id: 父技能ID（仅二级技能需要）

        Returns:
            新创建的 skill ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO skills (name, description, instructions, always_load, enabled, version, level, parent_skill_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, description, instructions, always_load, enabled, version, level, parent_skill_id))
            conn.commit()
            skill_id = cursor.lastrowid
            logger.info(f"[Database] 创建 Skill: {name} (ID: {skill_id}, Level: {level})")
            return skill_id
    
    def get_skill_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取 Skill"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM skills WHERE name = %s AND enabled = TRUE", (name,))
            row = cursor.fetchone()
            return row
    
    def get_skill_by_id(self, skill_id: int) -> Optional[Dict]:
        """根据 ID 获取 Skill"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM skills WHERE id = %s", (skill_id,))
            row = cursor.fetchone()
            return row
    
    def get_all_skills(self, enabled_only: bool = True) -> List[Dict]:
        """获取所有 Skills"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if enabled_only:
                cursor.execute("SELECT * FROM skills WHERE enabled = TRUE ORDER BY always_load DESC, name")
            else:
                cursor.execute("SELECT * FROM skills ORDER BY always_load DESC, name")
            rows = cursor.fetchall()
            return list(rows)
    
    def get_always_load_skills(self) -> List[Dict]:
        """获取始终加载的 Skills"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM skills WHERE always_load = TRUE AND enabled = TRUE")
            rows = cursor.fetchall()
            return list(rows)

    def get_top_level_skills(self, enabled_only: bool = True) -> List[Dict]:
        """获取所有一级技能（level=1 的技能）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if enabled_only:
                cursor.execute("SELECT * FROM skills WHERE level = 1 AND enabled = TRUE ORDER BY always_load DESC, name")
            else:
                cursor.execute("SELECT * FROM skills WHERE level = 1 ORDER BY always_load DESC, name")
            rows = cursor.fetchall()
            return list(rows)

    def get_child_skills(self, parent_skill_id: int, enabled_only: bool = True) -> List[Dict]:
        """获取指定技能的所有子技能"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if enabled_only:
                cursor.execute(
                    "SELECT * FROM skills WHERE parent_skill_id = %s AND enabled = TRUE ORDER BY name",
                    (parent_skill_id,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM skills WHERE parent_skill_id = %s ORDER BY name",
                    (parent_skill_id,)
                )
            rows = cursor.fetchall()
            return list(rows)

    def get_skills_by_level(self, level: int, enabled_only: bool = True) -> List[Dict]:
        """获取指定级别的所有技能"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if enabled_only:
                cursor.execute(
                    "SELECT * FROM skills WHERE level = %s AND enabled = TRUE ORDER BY name",
                    (level,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM skills WHERE level = %s ORDER BY name",
                    (level,)
                )
            rows = cursor.fetchall()
            return list(rows)
    
    def update_skill(
        self,
        skill_id: int,
        name: str = None,
        description: str = None,
        instructions: str = None,
        always_load: bool = None,
        enabled: bool = None,
        version: str = None,
        level: int = None,
        parent_skill_id: int = None
    ) -> bool:
        """更新 Skill"""
        updates = []
        values = []

        if name is not None:
            updates.append("name = %s")
            values.append(name)
        if description is not None:
            updates.append("description = %s")
            values.append(description)
        if instructions is not None:
            updates.append("instructions = %s")
            values.append(instructions)
        if always_load is not None:
            updates.append("always_load = %s")
            values.append(always_load)
        if enabled is not None:
            updates.append("enabled = %s")
            values.append(enabled)
        if version is not None:
            updates.append("version = %s")
            values.append(version)
        if level is not None:
            updates.append("level = %s")
            values.append(level)
        if parent_skill_id is not None:
            updates.append("parent_skill_id = %s")
            values.append(parent_skill_id if parent_skill_id != 0 else None)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(skill_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = f"UPDATE skills SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(query, values)
            conn.commit()
            logger.info(f"[Database] 更新 Skill ID: {skill_id}")
            return cursor.rowcount > 0
    
    def delete_skill(self, skill_id: int) -> bool:
        """删除 Skill（及其所有资源）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM skills WHERE id = %s", (skill_id,))
            conn.commit()
            logger.info(f"[Database] 删除 Skill ID: {skill_id}")
            return cursor.rowcount > 0
    
    # ==================== Resources CRUD ====================
    
    def add_resource(
        self,
        skill_id: int,
        resource_name: str,
        resource_type: str,
        content: str = None,
        file_path: str = None,
        description: str = None
    ) -> int:
        """
        添加资源到 Skill
        
        Args:
            skill_id: Skill ID
            resource_name: 资源名称（如 sqlmap_wrapper.py）
            resource_type: 资源类型（script, payload, template, data）
            content: 资源内容（文本）
            file_path: 资源文件路径（如果是大文件）
            description: 资源描述
            
        Returns:
            资源 ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO skill_resources 
                (skill_id, resource_name, resource_type, content, file_path, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (skill_id, resource_name, resource_type, content, file_path, description))
            conn.commit()
            resource_id = cursor.lastrowid
            logger.info(f"[Database] 添加资源: {resource_name} -> Skill ID: {skill_id}")
            return resource_id
    
    def get_skill_resources(self, skill_id: int) -> List[Dict]:
        """获取 Skill 的所有资源"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM skill_resources 
                WHERE skill_id = %s 
                ORDER BY resource_type, resource_name
            """, (skill_id,))
            rows = cursor.fetchall()
            return list(rows)
    
    def get_resource(self, skill_id: int, resource_name: str) -> Optional[Dict]:
        """获取指定资源"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM skill_resources 
                WHERE skill_id = %s AND resource_name = %s
            """, (skill_id, resource_name))
            row = cursor.fetchone()
            return row
    
    def get_resource_content(self, skill_id: int, resource_name: str) -> Optional[str]:
        """获取资源内容"""
        from pathlib import Path
        
        resource = self.get_resource(skill_id, resource_name)
        if not resource:
            return None
        
        # 如果有内容直接返回
        if resource.get('content'):
            return resource['content']
        
        # 如果是文件路径，读取文件
        if resource.get('file_path'):
            file_path = Path(resource['file_path'])
            if file_path.exists():
                return file_path.read_text(encoding='utf-8')
        
        return None
    
    def update_resource(
        self,
        resource_id: int,
        content: str = None,
        description: str = None
    ) -> bool:
        """更新资源"""
        updates = []
        values = []
        
        if content is not None:
            updates.append("content = %s")
            values.append(content)
        if description is not None:
            updates.append("description = %s")
            values.append(description)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(resource_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = f"UPDATE skill_resources SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_resource(self, resource_id: int) -> bool:
        """删除资源"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM skill_resources WHERE id = %s", (resource_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ==================== Metadata ====================
    
    def set_metadata(self, skill_id: int, key: str, value: Any) -> None:
        """设置 Skill 元数据"""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO skill_metadata (skill_id, meta_key, meta_value)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value)
            """, (skill_id, key, value_str))
            conn.commit()
    
    def get_metadata(self, skill_id: int, key: str) -> Optional[Any]:
        """获取 Skill 元数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT meta_value FROM skill_metadata 
                WHERE skill_id = %s AND meta_key = %s
            """, (skill_id, key))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['meta_value'])
                except:
                    return row['meta_value']
            return None


# 全局数据库实例
_db_instance: Optional[SkillsDatabase] = None


def get_database() -> SkillsDatabase:
    """获取全局数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = SkillsDatabase()
    return _db_instance
