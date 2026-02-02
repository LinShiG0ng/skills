# Anthropic Agent Skills - 数据包分析系统

## 项目简介

基于 **Anthropic Agent Skills 官方标准**实现的数据包分析和安全测试系统。

### 核心特性

✅ **标准 SKILL.md 格式** - YAML frontmatter + Markdown  
✅ **渐进披露机制** - Metadata → Instructions → Resources  
✅ **AI 自主判断** - 由 AI 基于 description 判断需要哪些 skills  
✅ **Level 3 Resources** - 支持脚本、payload、模板等资源  
✅ **数据包驱动** - 用户提供数据包，AI 调用对应 skill  

---

## 项目结构

```
prompt-router-demo/
├── router.py                 # 核心路由器（AI 判断 + Resources 支持）
├── server.py                 # API 服务器
├── skills_config.json        # Skills 配置
├── skills/                   # Skills 目录
│   ├── role_definition/      # 角色定义（always_load）
│   │   └── SKILL.md
│   └── sqlmap_scanner/       # SQLMap 扫描（按需加载）
│       ├── SKILL.md
│       └── resources/        # Level 3: 资源
│           ├── sqlmap_wrapper.py       # SQLMap 封装脚本
│           ├── request_generator.py    # 请求文件生成器
│           ├── payloads/
│           │   └── custom_payloads.txt # 自定义 payload
│           └── templates/
│               └── request_template.txt # 请求模板
├── web/                      # Web 界面
└── logs/                     # 日志目录
    ├── app.log               # 结构化日志
    └── prompts.log           # 提示词详细日志
```

---

## 快速开始

### 启动服务器

```bash
python server.py
```

### 使用流程

1. **用户提供 HTTP 数据包**

```http
POST /api/login HTTP/1.1
Host: target.com
Content-Type: application/x-www-form-urlencoded

username=admin&password=test
```

2. **AI 分析数据包**
   - 识别接口类型
   - 判断需要的 skill

3. **AI 调用对应 skill**
   - 如果是 SQL 注入测试 → 调用 `sqlmap_scanner` skill
   - 加载 skill 的 instructions 和 resources

4. **执行测试**
   - 使用 `resources/sqlmap_wrapper.py` 执行扫描
   - 或直接调用 SQLMap

5. **返回结果**
   - 分析漏洞
   - 给出专业建议

---

## Skills 说明

### 1. role_definition（核心）

- **类型**: always_load (始终加载)
- **用途**: 定义 AI 的角色和工作方式
- **内容**: 基于数据包的分析流程

### 2. sqlmap_scanner（专业）

- **类型**: optional (按需加载)
- **用途**: SQL 注入检测和利用
- **触发**: AI 判断需要时自动加载

**包含的 Resources (Level 3):**
- `sqlmap_wrapper.py` - Python 封装脚本
- `request_generator.py` - 请求文件生成器  
- `payloads/custom_payloads.txt` - Payload 集合
- `templates/request_template.txt` - 请求模板

---

## API 端点

### POST /api/chat

发送数据包进行分析。

**请求：**
```json
{
  "question": "请分析这个数据包:\nPOST /login HTTP/1.1\nHost: test.com\n...",
  "session_id": "optional"
}
```

**响应：**
```json
{
  "session_id": "session-xxx",
  "skills": ["role_definition", "sqlmap_scanner"],
  "newly_loaded_skills": ["sqlmap_scanner"],
  "answer": "分析结果..."
}
```

### GET /api/skills

获取所有可用 skills。

### GET /api/skills/{skill_name}/resources

获取指定 skill 的资源列表。

**示例：**
```bash
curl http://127.0.0.1:8010/api/skills/sqlmap_scanner/resources
```

**响应：**
```json
{
  "skill": "sqlmap_scanner",
  "resources": [
    "sqlmap_wrapper.py",
    "request_generator.py",
    "payloads/custom_payloads.txt",
    "templates/request_template.txt"
  ],
  "count": 4
}
```

### GET /api/skills/{skill_name}/resources/{resource_path}

获取指定资源的内容。

---

## 工作流程

```
用户提供数据包
    ↓
AI 分析数据包结构
    ↓
AI 判断需要 sqlmap_scanner skill
    ↓
系统加载 sqlmap_scanner 的：
  - Instructions (SKILL.md)
  - Resources (脚本、payload 等)
    ↓
AI 根据指导调用工具
    ↓
执行 SQLMap 扫描
    ↓
返回分析结果
```

---

## 日志

所有操作都会记录到：

- `logs/app.log` - 结构化日志（JSON）
- `logs/prompts.log` - 完整提示词和注入内容

---

## 三层加载示例

### Level 1: Metadata（始终存在）

```
Available Skills:
- role_definition: AI agent's identity...
- sqlmap_scanner: SQLMap integration for SQL injection...
```

### Level 2: Instructions（按需加载）

当 AI 判断需要 sqlmap_scanner 时，加载完整的 SKILL.md 内容。

### Level 3: Resources（实际使用时）

当需要具体脚本或 payload 时，AI 可以：
```python
# 获取 payload
wrapper.get_resource("payloads/custom_payloads.txt")

# 执行脚本
python skills/sqlmap_scanner/resources/sqlmap_wrapper.py --url ...
```

---

## 扩展

### 添加新的扫描 skill

1. 创建目录：`mkdir -p skills/new_scanner`
2. 创建 `SKILL.md`（YAML + Markdown）
3. 添加 `resources/` 目录（脚本、数据等）
4. 在 `skills_config.json` 中注册

---

## License

MIT
