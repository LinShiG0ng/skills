"""
支持数据库后端的 API 服务器
包含 Skills 管理 CRUD 接口 + 静态文件服务
"""

import json
import os
import sys
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import uuid

from logging_utils import log_event
from router_db import answer, get_skill_manager
from db_models import get_database

# 静态文件目录
BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"


class DBApiHandler(BaseHTTPRequestHandler):
    """支持数据库后端的 API 处理器"""
    
    def _send_json(self, status_code: int, payload: dict) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self) -> None:
        self._send_json(204, {})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        
        if parsed.path == "/api/chat":
            self._handle_chat()
        elif parsed.path == "/api/skills":
            self._handle_create_skill()
        elif parsed.path.startswith("/api/skills/") and parsed.path.endswith("/resources"):
            skill_id = self._extract_skill_id(parsed.path)
            if skill_id:
                self._handle_add_resource(skill_id)
            else:
                self._send_json(400, {"error": "Invalid skill ID"})
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        
        # API 路由
        if parsed.path == "/api/health":
            self._send_json(200, {
                "status": "ok", 
                "message": "Anthropic Skills Server (Database Backend)",
                "storage": "SQLite"
            })
        
        elif parsed.path == "/api/skills":
            self._handle_get_skills()

        elif parsed.path == "/api/skills/top-level":
            self._handle_get_top_level_skills()

        elif parsed.path.startswith("/api/skills/") and parsed.path.endswith("/children"):
            skill_id = self._parse_int(parsed.path.split("/")[3])
            if skill_id:
                self._handle_get_child_skills(skill_id)
            else:
                self._send_json(400, {"error": "Invalid skill ID"})
        
        elif parsed.path.startswith("/api/skills/") and parsed.path.endswith("/resources"):
            skill_id = self._extract_skill_id(parsed.path)
            if skill_id:
                self._handle_get_skill_resources(skill_id)
            else:
                self._send_json(400, {"error": "Invalid skill ID"})
        
        elif parsed.path.startswith("/api/skills/") and "/resources/" in parsed.path:
            parts = parsed.path.split("/")
            skill_id = self._parse_int(parts[3])
            resource_name = "/".join(parts[5:])
            if skill_id:
                self._handle_get_resource(skill_id, resource_name)
            else:
                self._send_json(400, {"error": "Invalid skill ID"})
        
        elif parsed.path.startswith("/api/skills/"):
            skill_id = self._extract_skill_id(parsed.path)
            if skill_id:
                self._handle_get_skill(skill_id)
            else:
                self._send_json(400, {"error": "Invalid skill ID"})
        
        elif parsed.path == "/api/db/stats":
            self._handle_db_stats()
        
        # 静态文件服务
        elif parsed.path.startswith("/web/") or parsed.path == "/" or parsed.path == "/web":
            self._serve_static_file(parsed.path)
        
        # 处理根目录下的静态文件请求 (style.css, app.js 等)
        elif parsed.path.endswith(('.css', '.js', '.html', '.ico', '.png', '.jpg', '.svg')):
            self._serve_static_file(f"/web{parsed.path}")
        
        else:
            self._send_json(404, {"error": "Not Found"})
    
    def _serve_static_file(self, path: str) -> None:
        """提供静态文件服务"""
        # 处理路径
        if path == "/" or path == "/web" or path == "/web/":
            path = "/web/index.html"
        
        # 移除 /web 前缀
        if path.startswith("/web/"):
            file_path = WEB_DIR / path[5:]
        else:
            file_path = WEB_DIR / path[1:]
        
        # 安全检查：确保路径在 web 目录下
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(WEB_DIR.resolve())):
                self._send_error(403, "Forbidden")
                return
        except Exception:
            self._send_error(400, "Bad Request")
            return
        
        # 检查文件是否存在
        if not file_path.exists() or not file_path.is_file():
            self._send_error(404, "File Not Found")
            return
        
        # 获取 MIME 类型
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"
        
        # 读取并发送文件
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_error(500, f"Internal Server Error: {e}")
    
    def _send_error(self, code: int, message: str) -> None:
        """发送错误响应"""
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<h1>{code} {message}</h1>".encode("utf-8"))

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        
        if parsed.path.startswith("/api/skills/"):
            skill_id = self._extract_skill_id(parsed.path)
            if skill_id:
                self._handle_update_skill(skill_id)
            else:
                self._send_json(400, {"error": "Invalid skill ID"})
        else:
            self._send_json(404, {"error": "Not Found"})
    
    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        
        if parsed.path.startswith("/api/session/"):
            session_id = parsed.path.split("/")[-1]
            self._handle_clear_session(session_id)
        
        elif parsed.path.startswith("/api/skills/"):
            skill_id = self._extract_skill_id(parsed.path)
            if skill_id:
                self._handle_delete_skill(skill_id)
            else:
                self._send_json(400, {"error": "Invalid skill ID"})
        
        else:
            self._send_json(404, {"error": "Not Found"})
    
    # ==================== Helper Methods ====================
    
    def _extract_skill_id(self, path: str) -> int:
        """从路径中提取 skill ID"""
        parts = path.split("/")
        if len(parts) >= 4:
            return self._parse_int(parts[3])
        return None
    
    def _parse_int(self, value: str) -> int:
        """安全解析整数"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _read_json_body(self) -> dict:
        """读取 JSON 请求体"""
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body) if body else {}

    # ==================== Chat Handler ====================

    def _handle_chat(self) -> None:
        """处理聊天请求"""
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        question = (payload.get("question") or "").strip()
        if not question:
            self._send_json(400, {"error": "Question is required"})
            return
        
        session_id = payload.get("session_id") or str(uuid.uuid4())

        try:
            result = answer(question, session_id)
            self._send_json(200, {
                "question": question,
                "session_id": result["session_id"],
                "skills": result["skills"],
                "newly_loaded_skills": result["newly_loaded_skills"],
                "answer": result["answer"]
            })
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": str(exc)})
    
    # ==================== Skills CRUD Handlers ====================
    
    def _handle_get_skills(self) -> None:
        """获取所有 Skills（包含层级信息）"""
        try:
            manager = get_skill_manager()
            skills_info = manager.get_skill_metadata_list()
            # 排序：先按 level，再按 always_load，最后按 name
            skills_info.sort(key=lambda s: (s.get("level", 1), not s["always_load"], s["name"]))

            self._send_json(200, {
                "total": len(skills_info),
                "storage": "database",
                "skills": skills_info
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def _handle_get_top_level_skills(self) -> None:
        """获取所有一级 Skills"""
        try:
            manager = get_skill_manager()
            skills_info = manager.get_top_level_skill_list()
            skills_info.sort(key=lambda s: (not s["always_load"], s["name"]))

            self._send_json(200, {
                "total": len(skills_info),
                "level": 1,
                "skills": skills_info
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def _handle_get_child_skills(self, parent_skill_id: int) -> None:
        """获取指定技能的子技能"""
        try:
            db = get_database()
            children = db.get_child_skills(parent_skill_id)

            self._send_json(200, {
                "parent_skill_id": parent_skill_id,
                "children": children,
                "count": len(children)
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
    
    def _handle_get_skill(self, skill_id: int) -> None:
        """获取单个 Skill 详情"""
        try:
            db = get_database()
            skill = db.get_skill_by_id(skill_id)

            if not skill:
                self._send_json(404, {"error": "Skill not found"})
                return

            # 确保返回的数据包含所有必要字段（兼容旧数据库）
            skill_data = dict(skill)
            skill_data.setdefault('level', 1)
            skill_data.setdefault('parent_skill_id', None)

            # 转换 datetime 对象为字符串
            from datetime import datetime
            for key, value in skill_data.items():
                if isinstance(value, datetime):
                    skill_data[key] = value.isoformat()

            # 获取资源列表
            resources = db.get_skill_resources(skill_id)
            skill_data['resources'] = resources
            skill_data['resources_count'] = len(resources)

            self._send_json(200, skill_data)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": str(exc)})
    
    def _handle_create_skill(self) -> None:
        """创建新的 Skill"""
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        # 验证必需字段
        required = ['name', 'description', 'instructions']
        for field in required:
            if not payload.get(field):
                self._send_json(400, {"error": f"Field '{field}' is required"})
                return

        # 验证 level 和 parent_skill_id 的逻辑一致性
        level = payload.get('level', 1)
        parent_skill_id = payload.get('parent_skill_id')

        # 一级技能不应有父技能
        if level == 1 and parent_skill_id:
            self._send_json(400, {"error": "一级技能不能有父技能"})
            return

        # 二级技能的父技能是可选的（通过 @use:skill_name 引用建立关系）

        try:
            db = get_database()

            # 检查名称是否已存在
            existing = db.get_skill_by_name(payload['name'])
            if existing:
                self._send_json(409, {"error": f"Skill '{payload['name']}' already exists"})
                return

            # 如果指定了父技能，验证父技能存在
            if parent_skill_id:
                parent = db.get_skill_by_id(parent_skill_id)
                if not parent:
                    self._send_json(400, {"error": f"父技能 ID {parent_skill_id} 不存在"})
                    return
                # 检查循环依赖（简单检查：父技能的 parent 不能是当前技能）
                # 更复杂的循环检测在实际场景中需要递归检查

            # 创建 Skill
            skill_id = db.create_skill(
                name=payload['name'],
                description=payload['description'],
                instructions=payload['instructions'],
                always_load=payload.get('always_load', False),
                enabled=payload.get('enabled', True),
                version=payload.get('version', '1.0.0'),
                level=level,
                parent_skill_id=parent_skill_id
            )

            # 重新加载 SkillManager
            get_skill_manager().reload_skills()

            self._send_json(201, {
                "message": "Skill created successfully",
                "id": skill_id,
                "name": payload['name'],
                "level": level,
                "parent_skill_id": parent_skill_id
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
    
    def _handle_update_skill(self, skill_id: int) -> None:
        """更新 Skill"""
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        try:
            db = get_database()

            # 检查是否存在
            existing = db.get_skill_by_id(skill_id)
            if not existing:
                self._send_json(404, {"error": "Skill not found"})
                return

            # 验证 level 和 parent_skill_id 的逻辑一致性
            level = payload.get('level')
            parent_skill_id = payload.get('parent_skill_id')

            # 一级技能不应有父技能
            if level is not None and level == 1 and parent_skill_id:
                self._send_json(400, {"error": "一级技能不能有父技能"})
                return
            # 二级技能的父技能是可选的

            # 防止自己成为自己的父技能
            if parent_skill_id and parent_skill_id == skill_id:
                self._send_json(400, {"error": "技能不能将自己设为父技能"})
                return

            # 更新
            success = db.update_skill(
                skill_id,
                name=payload.get('name'),
                description=payload.get('description'),
                instructions=payload.get('instructions'),
                always_load=payload.get('always_load'),
                enabled=payload.get('enabled'),
                version=payload.get('version'),
                level=level,
                parent_skill_id=parent_skill_id
            )

            if success:
                get_skill_manager().reload_skills()
                self._send_json(200, {"message": "Skill updated successfully", "id": skill_id})
            else:
                self._send_json(400, {"error": "No fields to update"})

        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
    
    def _handle_delete_skill(self, skill_id: int) -> None:
        """删除 Skill"""
        try:
            db = get_database()
            
            existing = db.get_skill_by_id(skill_id)
            if not existing:
                self._send_json(404, {"error": "Skill not found"})
                return
            
            success = db.delete_skill(skill_id)
            
            if success:
                get_skill_manager().reload_skills()
                self._send_json(200, {
                    "message": "Skill deleted successfully",
                    "id": skill_id,
                    "name": existing['name']
                })
            else:
                self._send_json(500, {"error": "Failed to delete skill"})
                
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
    
    # ==================== Resources Handlers ====================
    
    def _handle_get_skill_resources(self, skill_id: int) -> None:
        """获取 Skill 的资源列表"""
        try:
            db = get_database()
            resources = db.get_skill_resources(skill_id)
            
            self._send_json(200, {
                "skill_id": skill_id,
                "resources": resources,
                "count": len(resources)
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
    
    def _handle_get_resource(self, skill_id: int, resource_name: str) -> None:
        """获取资源内容"""
        try:
            db = get_database()
            content = db.get_resource_content(skill_id, resource_name)
            
            if content is None:
                self._send_json(404, {"error": "Resource not found"})
                return
            
            self._send_json(200, {
                "skill_id": skill_id,
                "resource": resource_name,
                "content": content
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
    
    def _handle_add_resource(self, skill_id: int) -> None:
        """添加资源到 Skill"""
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return
        
        required = ['resource_name', 'resource_type']
        for field in required:
            if not payload.get(field):
                self._send_json(400, {"error": f"Field '{field}' is required"})
                return
        
        try:
            db = get_database()
            
            resource_id = db.add_resource(
                skill_id=skill_id,
                resource_name=payload['resource_name'],
                resource_type=payload['resource_type'],
                content=payload.get('content'),
                file_path=payload.get('file_path'),
                description=payload.get('description')
            )
            
            self._send_json(201, {
                "message": "Resource added successfully",
                "id": resource_id,
                "skill_id": skill_id,
                "resource_name": payload['resource_name']
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
    
    # ==================== Session Handler ====================
    
    def _handle_clear_session(self, session_id: str) -> None:
        """清除会话"""
        try:
            manager = get_skill_manager()
            manager.clear_session(session_id)
            self._send_json(200, {
                "message": f"Session {session_id} cleared",
                "session_id": session_id
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
    
    # ==================== Database Stats ====================
    
    def _handle_db_stats(self) -> None:
        """获取数据库统计信息"""
        try:
            db = get_database()
            all_skills = db.get_all_skills(enabled_only=False)
            
            total_resources = 0
            for skill in all_skills:
                resources = db.get_skill_resources(skill['id'])
                total_resources += len(resources)
            
            self._send_json(200, {
                "database": db.db_path,
                "total_skills": len(all_skills),
                "enabled_skills": len([s for s in all_skills if s['enabled']]),
                "always_load_skills": len([s for s in all_skills if s['always_load']]),
                "total_resources": total_resources
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})


def run() -> None:
    host = os.environ.get("ROUTER_HOST", "127.0.0.1")
    port = int(os.environ.get("ROUTER_PORT", "8010"))
    server = HTTPServer((host, port), DBApiHandler)
    
    print("=" * 70)
    print("[*] Anthropic Agent Skills - Database Backend")
    print("=" * 70)
    print(f"Server: http://{host}:{port}")
    print()
    print("[Web Interface]")
    print(f"   http://{host}:{port}/web/index.html")
    print(f"   http://{host}:{port}/")
    print()
    print("Storage: SQLite Database")
    print()
    print("API Endpoints:")
    print(f"  POST   /api/chat                   - Chat Analysis")
    print(f"  GET    /api/skills                 - Get All Skills")
    print(f"  POST   /api/skills                 - Create Skill")
    print(f"  GET    /api/skills/{{id}}           - Get Skill Detail")
    print(f"  PUT    /api/skills/{{id}}           - Update Skill")
    print(f"  DELETE /api/skills/{{id}}           - Delete Skill")
    print(f"  GET    /api/skills/{{id}}/resources - Get Resources")
    print(f"  POST   /api/skills/{{id}}/resources - Add Resource")
    print(f"  GET    /api/db/stats               - DB Stats")
    print(f"  DELETE /api/session/{{id}}          - Clear Session")
    print("=" * 70)
    
    # Preload
    get_skill_manager()
    
    db = get_database()
    print(f"\n[Database] {db.db_path}")
    skills = db.get_all_skills()
    print(f"   Loaded {len(skills)} Skills")
    
    print("\n[*] Server started, waiting for requests...")
    print(f"[*] Open browser: http://{host}:{port}/\n")
    
    server.serve_forever()


if __name__ == "__main__":
    run()

