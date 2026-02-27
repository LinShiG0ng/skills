# 快速开始

## 系统概述

基于文件读取 + 数据库镜像的智能技能管理系统：

- **问答速度快** — 技能从本地文件读取，无数据库访问
- **后台可管理** — 前端 CRUD 同步到数据库，便于后台查看
- **层级化技能** — 一级/二级技能通过目录划分

---

## 1. 环境准备

### 安装依赖

```bash
pip install pymysql pyyaml
```

### 配置数据库（可选）

默认配置已内置，如需修改：

```bash
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=123.com
export MYSQL_DATABASE=skills
```

### 配置 AI API

```bash
export DASHSCOPE_API_KEY=your_api_key
```

---

## 2. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS skills CHARACTER SET utf8mb4"

# 导入表结构和初始数据
mysql -u root -p skills < skills_mysql.sql
```

---

## 3. 启动服务器

```bash
cd prompt-router-demo
python server_db.py
```

输出：
```
======================================================================
[*] Anthropic Agent Skills — File + DB Mirror
======================================================================

[Storage] 技能从本地文件读取（skills/L1/ 和 skills/L2/）
[Mirror]  前端 CRUD 同步写入 DB，供后台查看

[Web] http://127.0.0.1:8010/

======================================================================
[Migration] DB→File: role_definition (Level 1)
[Migration] DB→File: sqlmap_scanner (Level 1)
[Migration] 已从 DB 导出 2 个技能到本地文件

[FileSkillManager] 2 skills loaded from files

[*] Server started, waiting for requests...
[*] Open browser: http://127.0.0.1:8010/
```

**首次启动时**：系统自动将数据库中的技能导出到本地文件目录。

---

## 4. 打开 Web 界面

浏览器访问：`http://127.0.0.1:8010/`

### 对话视图

1. 在输入框输入问题
2. 点击「发送」或按 Enter
3. 查看 AI 回复和涉及的技能

### 技能管理视图

1. 点击顶部「技能管理」标签
2. 左侧显示一级技能，右侧显示二级技能
3. 点击「新建技能」创建新技能
4. 点击「编辑」或「删除」管理现有技能

---

## 5. 技能目录结构

```
skills/
├── L1/                    # 一级技能（AI 可直接加载）
│   ├── role_definition.md
│   └── sqlmap_scanner.md
└── L2/                    # 二级技能（通过 @use: 引用）
    └── (二级技能文件)
```

### 技能文件格式

```markdown
---
name: my_skill
description: 技能描述，AI 用于判断是否加载
always_load: false
enabled: true
version: 1.0.0
---

# Instructions

这里是技能的详细指令...

## 引用其他技能

可以使用 @use:other_skill 来引用二级技能
```

---

## 6. 创建技能示例

### 通过 Web 界面

1. 点击「技能管理」→「新建技能」
2. 填写：
   - 名称：`my_new_skill`
   - 描述：`这是一个新技能`
   - 级别：选择「一级技能」或「二级技能」
   - 指令：填写详细内容
3. 点击「保存」

### 通过 API

```bash
curl -X POST http://127.0.0.1:8010/api/skills \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_new_skill",
    "description": "这是一个新技能",
    "instructions": "详细指令内容...",
    "level": 1,
    "always_load": false
  }'
```

### 直接创建文件

在 `skills/L1/` 或 `skills/L2/` 目录下创建 `.md` 文件，重启服务器即可加载。

---

## 7. 引用子技能

在一级技能的 instructions 中使用 `@use:skill_name` 引用二级技能：

```markdown
---
name: parent_skill
description: 父技能
always_load: false
version: 1.0.0
---

# Instructions

当需要执行某操作时，使用以下子技能：

@use:child_skill_a
@use:child_skill_b

根据情况选择合适的子技能...
```

系统会自动递归加载被引用的技能（支持二级技能引用其他二级技能）。

---

## 8. API 使用

### 发送问题

```bash
curl -X POST http://127.0.0.1:8010/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "请分析这个数据包...",
    "session_id": "user123"
  }'
```

### 获取所有技能

```bash
curl http://127.0.0.1:8010/api/skills
```

### 获取技能详情

```bash
curl http://127.0.0.1:8010/api/skills/1
```

### 清除会话

```bash
curl -X DELETE http://127.0.0.1:8010/api/session/user123
```

---

## 9. 数据流说明

```
┌─────────────────────────────────────────────────────────┐
│                    用户操作                              │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
   问答/对话                    CRUD 操作
        │                           │
        ▼                           ▼
 ┌──────────────┐           ┌──────────────┐
 │ 读取本地文件  │           │ 写入本地文件  │
 │ (速度快)     │           │      +       │
 └──────────────┘           │ 同步到 DB    │
                            └──────────────┘
```

---

## 10. 日志查看

### 提示词日志

```bash
cat logs/prompts.log
```

查看每次对话注入的完整内容。

### 结构化日志

```bash
cat logs/app.log | tail -1 | python -m json.tool
```

---

## 11. 常见问题

### Q: 修改了技能文件，如何生效？

重启服务器，或通过 Web 界面编辑后保存。

### Q: 数据库中的技能没有同步到文件？

首次启动时会自动迁移。如需手动迁移，删除 `skills/L1/` 和 `skills/L2/` 中的文件后重启。

### Q: 二级技能没有被加载？

检查一级技能的 instructions 中是否正确使用了 `@use:skill_name` 语法。

---

## 12. 下一步

- 查看 `README.md` 了解完整架构
- 查看 `logs/prompts.log` 查看实际注入的内容
- 通过 Web 界面管理技能
