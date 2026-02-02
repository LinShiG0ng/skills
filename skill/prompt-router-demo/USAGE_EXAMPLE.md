# 使用示例

## 完整工作流程

### 1. 用户提供 HTTP 数据包

```
用户: "请帮我分析这个数据包是否存在SQL注入：

POST /api/user/login HTTP/1.1
Host: target.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 35

username=admin&password=test123
```

### 2. AI 分析并判断需要的 skill

```
[AI 判断流程]
1. 解析数据包：POST 请求，登录接口，有 username 和 password 参数
2. 判断任务类型：SQL 注入检测
3. 调用 AI 判断器：
   问题："请帮我分析这个数据包是否存在SQL注入"
   可用 skills: sqlmap_scanner
   → AI 返回: "sqlmap_scanner"
4. 加载 sqlmap_scanner skill 的完整内容和 resources
```

### 3. AI 调用 skill 中的工具

```
AI: "好的，我来帮你检测这个登录接口是否存在 SQL 注入。

我会使用 SQLMap 进行检测。首先生成请求文件..."

[AI 执行]
1. 创建请求文件 request.txt
2. 调用 sqlmap_wrapper.py
3. 执行扫描
```

### 4. 返回分析结果

```
AI: "扫描完成。结果如下：

✅ 发现 SQL 注入漏洞！
- 参数: username
- 类型: Boolean-based blind
- 数据库: MySQL 5.7

建议：
1. 立即修复该漏洞
2. 使用参数化查询
3. 添加输入验证
..."
```

---

## 日志记录

### prompts.log 内容

```
================================================================================
SESSION: session-xxx
TIMESTAMP: 2026-01-21T15:00:00
================================================================================

[USER QUESTION]
请帮我分析这个数据包是否存在SQL注入：
POST /api/user/login HTTP/1.1
...

================================================================================
[METADATA]
================================================================================
Skills Involved: role_definition, sqlmap_scanner
Newly Loaded: sqlmap_scanner
Prompt Length: 3500 chars
Estimated Tokens: ~875

================================================================================
[SYSTEM PROMPT]
================================================================================
# Available Skills

## Core Skills (Always Active)
- **role_definition**: AI agent's identity as a security testing specialist...

## Specialized Skills (Activated On-Demand)
- **sqlmap_scanner**: SQLMap integration for SQL injection testing...

============================================================
# Activated Skills

## Skill: sqlmap_scanner

# SQLMap Scanner Skill

## Overview
本技能用于基于用户提供的 HTTP 数据包进行 SQL 注入检测...

## Workflow
...完整的使用指导...

## Available Resources
- resources/sqlmap_wrapper.py - SQLMap 封装类
...

================================================================================
[FULL MESSAGES SENT TO AI]
================================================================================
[
  {
    "role": "system",
    "content": "<完整的 system prompt>"
  },
  {
    "role": "user",
    "content": "请帮我分析这个数据包..."
  }
]
```

---

## Skill Resources 调用示例

### 在代码中调用

```python
from router import get_skill_manager

manager = get_skill_manager()

# 列出 sqlmap_scanner 的所有资源
resources = manager.list_skill_resources("sqlmap_scanner")
print(resources)
# ['sqlmap_wrapper.py', 'request_generator.py', ...]

# 获取 payload 内容
payload_content = manager.get_skill_resource(
    "sqlmap_scanner",
    "payloads/custom_payloads.txt"
)
print(payload_content)
```

### 通过 API 调用

```bash
# 列出资源
curl http://127.0.0.1:8010/api/skills/sqlmap_scanner/resources

# 获取资源内容
curl http://127.0.0.1:8010/api/skills/sqlmap_scanner/resources/payloads/custom_payloads.txt
```

---

## 第二次对话（复用）

```
用户: "继续测试 password 参数"

[AI 判断]
- sqlmap_scanner 已加载 ✅
- 不需要重新加载

[System Prompt]
- 只包含元数据（~200 tokens）
- 不包含 sqlmap_scanner 的完整内容
- 但历史对话中已有该 skill 的上下文

AI: "好的，我继续测试 password 参数..."
[直接调用 resources 中的脚本]
```

**Token 节省：~1600 tokens (80%)**

---

## 多个数据包的处理

```
用户: "我有3个数据包，分别测试：

1. POST /login ...
2. GET /user?id=1 ...
3. POST /search ...
"

AI:
1. 第一个数据包已加载 sqlmap_scanner skill
2. 测试第一个（调用 resources/sqlmap_wrapper.py）
3. 测试第二个（复用 skill，直接调用）
4. 测试第三个（复用 skill，直接调用）

所有测试只需要加载一次 skill！
```

---

## 总结

- **用户**: 提供数据包
- **AI**: 判断需要哪个 skill
- **系统**: 按需加载 skill（包含 resources）
- **AI**: 调用 resources 中的脚本执行测试
- **后续**: 复用已加载的 skill，大幅节省 token





