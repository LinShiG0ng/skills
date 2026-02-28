"""
Anthropic Agent Skills - API 服务器

架构：
  - LLM 读取技能：从本地文件（skills/L1/ 和 skills/L2/）快速加载
  - 前端 CRUD：写入本地文件 + 同步到数据库（镜像，供后台查看）
"""

import json
import os
import sys
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from datetime import datetime
import uuid

from logging_utils import log_event
from router_file import answer, answer_stream, get_skill_manager, _write_skill_file, _delete_skill_file
from db_models import get_database

BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"


class DBApiHandler(BaseHTTPRequestHandler):

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
        elif parsed.path == "/api/chat/stream":
            self._handle_chat_stream()
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

        if parsed.path == "/api/health":
            self._send_json(200, {"status": "ok", "storage": "file+db-mirror"})

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

        elif parsed.path.startswith("/web/") or parsed.path in ("/", "/web"):
            self._serve_static_file(parsed.path)

        elif parsed.path.endswith(('.css', '.js', '.html', '.ico', '.png', '.jpg', '.svg')):
            self._serve_static_file(f"/web{parsed.path}")

        else:
            self._send_json(404, {"error": "Not Found"})

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
            self._handle_clear_session(parsed.path.split("/")[-1])
        elif parsed.path.startswith("/api/skills/"):
            skill_id = self._extract_skill_id(parsed.path)
            if skill_id:
                self._handle_delete_skill(skill_id)
            else:
                self._send_json(400, {"error": "Invalid skill ID"})
        else:
            self._send_json(404, {"error": "Not Found"})

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _extract_skill_id(self, path: str):
        parts = path.split("/")
        return self._parse_int(parts[3]) if len(parts) >= 4 else None

    def _parse_int(self, value: str):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body) if body else {}

    def _serve_static_file(self, path: str) -> None:
        if path in ("/", "/web", "/web/"):
            path = "/web/index.html"
        file_path = WEB_DIR / (path[5:] if path.startswith("/web/") else path[1:])
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(WEB_DIR.resolve())):
                self._send_error(403, "Forbidden")
                return
        except Exception:
            self._send_error(400, "Bad Request")
            return
        if not file_path.exists() or not file_path.is_file():
            self._send_error(404, "File Not Found")
            return
        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_error(500, f"Internal Server Error: {e}")

    def _send_error(self, code: int, message: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<h1>{code} {message}</h1>".encode("utf-8"))

    # ------------------------------------------------------------------ #
    #  Chat                                                                #
    # ------------------------------------------------------------------ #

    def _handle_chat(self) -> None:
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
            # answer() 读取本地文件，无 DB 访问
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

    def _handle_chat_stream(self) -> None:
        """流式聊天 - 使用 Server-Sent Events"""
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
            # 发送 SSE 响应头
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # 流式获取响应
            full_answer = ""
            for event_type, data in answer_stream(question, session_id):
                if event_type == "meta":
                    # 发送元数据（技能信息）
                    event_data = json.dumps(data, ensure_ascii=False)
                    self.wfile.write(f"event: meta\ndata: {event_data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                elif event_type == "chunk":
                    # 发送内容块
                    full_answer += data
                    chunk_data = json.dumps({"content": data}, ensure_ascii=False)
                    self.wfile.write(f"event: chunk\ndata: {chunk_data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                elif event_type == "done":
                    # 发送完成信号
                    done_data = json.dumps({"answer": full_answer}, ensure_ascii=False)
                    self.wfile.write(f"event: done\ndata: {done_data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                elif event_type == "error":
                    # 发送错误信息
                    error_data = json.dumps({"error": data}, ensure_ascii=False)
                    self.wfile.write(f"event: error\ndata: {error_data}\n\n".encode("utf-8"))
                    self.wfile.flush()

        except Exception as exc:
            import traceback
            traceback.print_exc()
            try:
                error_data = json.dumps({"error": str(exc)}, ensure_ascii=False)
                self.wfile.write(f"event: error\ndata: {error_data}\n\n".encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Skills CRUD — 写文件 + 同步 DB                                      #
    # ------------------------------------------------------------------ #

    def _handle_get_skills(self) -> None:
        """从内存（文件缓存）返回技能列表。"""
        try:
            manager = get_skill_manager()
            skills_info = manager.get_skill_metadata_list()
            skills_info.sort(key=lambda s: (s.get("level", 1), not s["always_load"], s["name"]))
            self._send_json(200, {
                "total": len(skills_info),
                "storage": "file",
                "skills": skills_info
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def _handle_get_top_level_skills(self) -> None:
        try:
            manager = get_skill_manager()
            skills_info = manager.get_top_level_skill_list()
            skills_info.sort(key=lambda s: (not s["always_load"], s["name"]))
            self._send_json(200, {"total": len(skills_info), "level": 1, "skills": skills_info})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def _handle_get_child_skills(self, parent_skill_id: int) -> None:
        """从 DB 镜像查询子技能。"""
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
        """从 DB 镜像读取技能详情（用于编辑表单）。"""
        try:
            db = get_database()
            skill = db.get_skill_by_id(skill_id)
            if not skill:
                self._send_json(404, {"error": "Skill not found"})
                return

            skill_data = dict(skill)
            skill_data.setdefault('level', 1)
            skill_data.setdefault('parent_skill_id', None)

            # datetime → 字符串
            for key, value in skill_data.items():
                if isinstance(value, datetime):
                    skill_data[key] = value.isoformat()

            resources = db.get_skill_resources(skill_id)
            skill_data['resources'] = resources
            skill_data['resources_count'] = len(resources)
            self._send_json(200, skill_data)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": str(exc)})

    def _handle_create_skill(self) -> None:
        """创建技能：写本地文件 + 同步到 DB。"""
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        for field in ('name', 'description', 'instructions'):
            if not payload.get(field):
                self._send_json(400, {"error": f"Field '{field}' is required"})
                return

        level = payload.get('level', 1)
        parent_skill_id = payload.get('parent_skill_id') or None

        if level == 1 and parent_skill_id:
            self._send_json(400, {"error": "一级技能不能有父技能"})
            return

        name = payload['name']
        description = payload['description']
        instructions = payload['instructions']
        always_load = payload.get('always_load', False)
        enabled = payload.get('enabled', True)
        version = payload.get('version', '1.0.0')

        try:
            db = get_database()

            # 检查名称是否已存在
            if db.get_skill_by_name(name):
                self._send_json(409, {"error": f"Skill '{name}' already exists"})
                return

            # 1. 写本地文件
            _write_skill_file(
                level=level,
                name=name,
                description=description,
                instructions=instructions,
                always_load=always_load,
                version=version,
                enabled=enabled,
            )

            # 2. 同步到 DB（镜像）
            skill_id = db.create_skill(
                name=name,
                description=description,
                instructions=instructions,
                always_load=always_load,
                enabled=enabled,
                version=version,
                level=level,
                parent_skill_id=parent_skill_id,
            )

            # 3. 重新扫描文件，刷新内存缓存
            get_skill_manager().reload_skills()

            self._send_json(201, {
                "message": "Skill created successfully",
                "id": skill_id,
                "name": name,
                "level": level,
                "storage": "file+db-mirror",
            })
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": str(exc)})

    def _handle_update_skill(self, skill_id: int) -> None:
        """更新技能：更新本地文件 + 同步到 DB。"""
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        try:
            db = get_database()
            existing = db.get_skill_by_id(skill_id)
            if not existing:
                self._send_json(404, {"error": "Skill not found"})
                return

            existing = dict(existing)
            level = payload.get('level', existing.get('level', 1))
            parent_skill_id = payload.get('parent_skill_id') or None
            old_name = existing['name']
            new_name = payload.get('name', old_name)
            old_level = existing.get('level', 1)

            if level == 1 and parent_skill_id:
                self._send_json(400, {"error": "一级技能不能有父技能"})
                return
            if parent_skill_id and parent_skill_id == skill_id:
                self._send_json(400, {"error": "技能不能将自己设为父技能"})
                return

            description = payload.get('description', existing['description'])
            instructions = payload.get('instructions', existing['instructions'])
            always_load = payload.get('always_load', existing.get('always_load', False))
            enabled = payload.get('enabled', existing.get('enabled', True))
            version = payload.get('version', existing.get('version', '1.0.0'))

            # 1. 删除旧文件（名称或 level 可能改变）
            _delete_skill_file(old_level, old_name)

            # 2. 写新文件
            _write_skill_file(
                level=level,
                name=new_name,
                description=description,
                instructions=instructions,
                always_load=bool(always_load),
                version=version,
                enabled=bool(enabled),
            )

            # 3. 同步更新 DB
            db.update_skill(
                skill_id,
                name=new_name,
                description=description,
                instructions=instructions,
                always_load=always_load,
                enabled=enabled,
                version=version,
                level=level,
                parent_skill_id=parent_skill_id,
            )

            # 4. 刷新内存缓存
            get_skill_manager().reload_skills()

            self._send_json(200, {
                "message": "Skill updated successfully",
                "id": skill_id,
                "storage": "file+db-mirror",
            })
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": str(exc)})

    def _handle_delete_skill(self, skill_id: int) -> None:
        """删除技能：删除本地文件 + 同步 DB。"""
        try:
            db = get_database()
            existing = db.get_skill_by_id(skill_id)
            if not existing:
                self._send_json(404, {"error": "Skill not found"})
                return

            existing = dict(existing)
            name = existing['name']
            level = existing.get('level', 1)

            # 1. 删除本地文件
            _delete_skill_file(level, name)

            # 2. 同步删除 DB
            db.delete_skill(skill_id)

            # 3. 刷新内存缓存
            get_skill_manager().reload_skills()

            self._send_json(200, {
                "message": "Skill deleted successfully",
                "id": skill_id,
                "name": name,
                "storage": "file+db-mirror",
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    # ------------------------------------------------------------------ #
    #  Resources（仍从 DB 镜像读写）                                        #
    # ------------------------------------------------------------------ #

    def _handle_get_skill_resources(self, skill_id: int) -> None:
        try:
            db = get_database()
            resources = db.get_skill_resources(skill_id)
            self._send_json(200, {"skill_id": skill_id, "resources": resources, "count": len(resources)})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def _handle_get_resource(self, skill_id: int, resource_name: str) -> None:
        try:
            db = get_database()
            content = db.get_resource_content(skill_id, resource_name)
            if content is None:
                self._send_json(404, {"error": "Resource not found"})
                return
            self._send_json(200, {"skill_id": skill_id, "resource": resource_name, "content": content})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def _handle_add_resource(self, skill_id: int) -> None:
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return
        for field in ('resource_name', 'resource_type'):
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
                description=payload.get('description'),
            )
            self._send_json(201, {
                "message": "Resource added successfully",
                "id": resource_id,
                "skill_id": skill_id,
                "resource_name": payload['resource_name'],
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    # ------------------------------------------------------------------ #
    #  Session                                                             #
    # ------------------------------------------------------------------ #

    def _handle_clear_session(self, session_id: str) -> None:
        try:
            get_skill_manager().clear_session(session_id)
            self._send_json(200, {"message": f"Session {session_id} cleared", "session_id": session_id})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    # ------------------------------------------------------------------ #
    #  DB Stats                                                            #
    # ------------------------------------------------------------------ #

    def _handle_db_stats(self) -> None:
        try:
            db = get_database()
            all_skills = db.get_all_skills(enabled_only=False)
            total_resources = sum(len(db.get_skill_resources(s['id'])) for s in all_skills)
            manager = get_skill_manager()
            from router_file import L1_DIR, L2_DIR
            self._send_json(200, {
                "storage": "file+db-mirror",
                "skills_dir": str(BASE_DIR / "skills"),
                "l1_dir": str(L1_DIR),
                "l2_dir": str(L2_DIR),
                "files_in_memory": len(manager.skills),
                "db_mirror_total_skills": len(all_skills),
                "db_mirror_resources": total_resources,
            })
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})


# ------------------------------------------------------------------ #
#  启动                                                                #
# ------------------------------------------------------------------ #

def run() -> None:
    host = os.environ.get("ROUTER_HOST", "127.0.0.1")
    port = int(os.environ.get("ROUTER_PORT", "8010"))
    server = HTTPServer((host, port), DBApiHandler)

    print("=" * 70)
    print("[*] Anthropic Agent Skills — File + DB Mirror")
    print("=" * 70)
    print(f"\n[Storage] 技能从本地文件读取（skills/L1/ 和 skills/L2/）")
    print(f"[Mirror]  前端 CRUD 同步写入 DB，供后台查看")
    print(f"\n[Web] http://{host}:{port}/\n")
    print("=" * 70)

    # 启动时：先从 DB 镜像导出已有技能到文件（如果文件不存在）
    _sync_db_to_files_on_startup()

    # 初始化文件路由器
    manager = get_skill_manager()
    print(f"\n[FileSkillManager] {len(manager.skills)} skills loaded from files")

    print("\n[*] Server started, waiting for requests...")
    print(f"[*] Open browser: http://{host}:{port}/\n")
    server.serve_forever()


def _sync_db_to_files_on_startup() -> None:
    """
    启动时检查：如果 DB 中有技能但本地文件不存在，
    则自动导出到文件（首次迁移用）。
    """
    from router_file import L1_DIR, L2_DIR, _write_skill_file
    try:
        db = get_database()
        all_skills = db.get_all_skills(enabled_only=False)
        if not all_skills:
            return

        migrated = 0
        for skill in all_skills:
            skill = dict(skill)
            level = skill.get('level', 1)
            name = skill['name']

            # 检查文件是否已存在
            import re
            directory = L1_DIR if level == 1 else L2_DIR
            filename = re.sub(r'[^\w\-]', '_', name) + ".md"
            file_path = directory / filename

            if not file_path.exists():
                _write_skill_file(
                    level=level,
                    name=name,
                    description=skill.get('description', ''),
                    instructions=skill.get('instructions', ''),
                    always_load=bool(skill.get('always_load', False)),
                    version=skill.get('version', '1.0.0'),
                    enabled=bool(skill.get('enabled', True)),
                )
                migrated += 1
                print(f"[Migration] DB→File: {name} (Level {level})")

        if migrated:
            print(f"[Migration] 已从 DB 导出 {migrated} 个技能到本地文件")
        else:
            print(f"[Migration] 本地文件已是最新，无需导出")

    except Exception as e:
        print(f"[Migration] 启动迁移失败（可跳过）: {e}")


if __name__ == "__main__":
    run()
