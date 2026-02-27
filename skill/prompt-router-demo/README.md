# Anthropic Agent Skills - 渐进披露架构

## 项目简介

基于 **Anthropic Agent Skills** 标准实现的智能技能管理系统，支持层级化技能结构和渐进披露机制。

### 核心特性

- **文件读取 + DB 镜像** — LLM 从本地文件快速读取技能，前端 CRUD 同步到数据库（供后台查看）
- **层级化技能** — L1 一级技能（AI 可直接加载）+ L2 二级技能（通过 `@use:` 引用加载）
- **渐进披露** — Metadata → Instructions → 递归引用 → Resources
- **AI 自主判断** — 由 AI 基于 description 判断需要哪些技能
- **Web 管理界面** — 可视化创建、编辑、删除技能

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 Web 界面                           │
│              (对话 + 技能管理 CRUD)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   server_db.py                              │
│                                                             │
│   CRUD 操作:  写本地文件 ──────► 同步到 DB 镜像              │
│   问答操作:   读本地文件（无 DB 访问，速度快）               │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│  skills/L1/     │       │  skills/L2/     │
│  一级技能 .md   │       │  二级技能 .md   │
│  (AI 可直接加载)│       │  (@use: 引用)   │
└─────────────────┘       └─────────────────┘
```

---

## 目录结构

```
prompt-router-demo/
├── server_db.py          # API 服务器（文件+DB镜像）
├── router_file.py        # 文件版路由器（核心）
├── router_db.py          # 数据库版路由器（备用）
├── db_models.py          # MySQL 数据库模型
├── qwen_client.py        # AI 客户端
├── logging_utils.py      # 日志工具
│
├── skills/               # 技能文件目录 ⭐
│   ├── L1/               # 一级技能（AI 可直接加载）
│   │   ├── role_definition.md
│   │   └── sqlmap_scanner.md
│   └── L2/               # 二级技能（通过引用加载）
│       └── (二级技能文件)
│
├── web/                  # Web 前端
│   ├── index.html        # 主页面（对话 + 技能管理）
│   ├── app.js            # 前端逻辑
│   └── style.css         # 样式
│
├── logs/                 # 日志目录
│   ├── app.log           # 结构化日志
│   └── prompts.log       # 提示词详细日志
│
└── skills_mysql.sql      # 数据库初始化脚本
```

---

## 技能文件格式 (SKILL.md)

```markdown
---
name: skill_name
description: 简短描述，供 AI 判断是否需要加载
always_load: false
enabled: true
version: 1.0.0
---

# Instructions

详细指令内容...

## 引用子技能

可以使用 @use:other_skill_name 语法引用二级技能，
系统会自动递归加载被引用的技能。
```

---

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install pymysql pyyaml

# 设置环境变量（可选，默认值已配置）
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=123.com
export MYSQL_DATABASE=skills

export DASHSCOPE_API_KEY=your_api_key
```

### 2. 初始化数据库

```bash
mysql -u root -p skills < skills_mysql.sql
```

### 3. 启动服务器

```bash
cd prompt-router-demo
python server_db.py
```

启动时会自动：
1. 检查 DB 中是否有已存在的技能
2. 将技能导出到 `skills/L1/` 或 `skills/L2/` 目录（首次迁移）
3. 从本地文件加载技能到内存

### 4. 访问 Web 界面

打开浏览器：`http://127.0.0.1:8010/`

---

## Web 界面功能

### 对话视图

- 输入问题，AI 自动判断需要的技能
- 显示涉及的技能和新加载的技能
- 对话历史记录

### 技能管理视图

- **双列布局**：左侧一级技能，右侧二级技能
- **创建技能**：填写名称、描述、指令，选择层级
- **编辑技能**：修改任意字段
- **删除技能**：确认后删除

---

## API 端点

### 对话

```
POST /api/chat
```

请求：
```json
{
  "question": "请分析这个数据包...",
  "session_id": "optional"
}
```

响应：
```json
{
  "session_id": "session-xxx",
  "skills": ["role_definition", "sqlmap_scanner"],
  "newly_loaded_skills": ["sqlmap_scanner"],
  "answer": "分析结果..."
}
```

### 技能管理

```
GET    /api/skills                 # 获取所有技能
GET    /api/skills/top-level       # 获取一级技能
POST   /api/skills                 # 创建技能
GET    /api/skills/{id}            # 获取技能详情
PUT    /api/skills/{id}            # 更新技能
DELETE /api/skills/{id}            # 删除技能
GET    /api/skills/{id}/children   # 获取子技能
```

### 资源管理

```
GET    /api/skills/{id}/resources           # 获取资源列表
POST   /api/skills/{id}/resources           # 添加资源
GET    /api/skills/{id}/resources/{name}    # 获取资源内容
```

### 会话管理

```
DELETE /api/session/{id}           # 清除会话
```

### 系统信息

```
GET    /api/health                 # 健康检查
GET    /api/db/stats               # 存储统计
```

---

## 渐进披露机制

### Level 1: 元数据摘要（始终存在）

```
Available Skills:
- role_definition: AI agent's identity...
- sqlmap_scanner: SQLMap integration for SQL injection...
```

### Level 2: 完整 Instructions（按需加载）

当 AI 判断需要某技能时，加载完整的 SKILL.md 内容。

### Level 2.5: 递归引用（自动加载）

当一级技能中包含 `@use:skill_name` 时，自动加载被引用的二级技能。
支持任意深度的引用链（带循环引用保护）。

### Level 3: Resources（实际使用时）

需要具体脚本或数据时，AI 可以请求加载资源内容。

---

## 技能层级说明

### 一级技能 (L1)

- 存放在 `skills/L1/` 目录
- AI 可直接判断并加载
- 元数据出现在初始摘要中
- 可设置 `always_load: true` 始终加载

### 二级技能 (L2)

- 存放在 `skills/L2/` 目录
- 通过 `@use:skill_name` 引用加载
- 元数据不出现在初始摘要中
- 支持二级技能引用其他二级技能

---

## 存储机制

| 操作 | 本地文件 | 数据库镜像 |
|------|---------|-----------|
| 问答读取 | ✅ 使用 | ❌ 不访问 |
| 创建技能 | ✅ 写入 | ✅ 同步 |
| 更新技能 | ✅ 写入 | ✅ 同步 |
| 删除技能 | ✅ 删除 | ✅ 同步 |
| 获取详情 | - | ✅ 读取 |

**优势**：
- LLM 问答时零数据库访问，速度大幅提升
- 后台可通过数据库查看所有用户创建的技能

---

## 日志

- `logs/app.log` — 结构化 JSON 日志
- `logs/prompts.log` — 完整提示词和 messages 记录

---

## 扩展

### 添加新技能

1. 在 `skills/L1/` 或 `skills/L2/` 创建 `.md` 文件
2. 使用 YAML frontmatter 定义元数据
3. 重启服务器或通过 Web 界面创建

### 引用其他技能

在 instructions 中使用：
```
@use:other_skill_name
```

系统会自动递归加载被引用的技能。

---

## License

MIT
