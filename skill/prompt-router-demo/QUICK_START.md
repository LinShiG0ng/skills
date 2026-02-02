# 快速开始

## 系统概述

一个基于 Anthropic Agent Skills 的数据包分析系统：
- 用户提供 HTTP 数据包
- AI 分析并调用对应的 skill
- 执行安全测试并返回结果

---

## 1. 启动服务器

```bash
cd prompt-router-demo
python server.py
```

输出：
```
======================================================================
🚀 Anthropic Agent Skills - 数据包分析系统
======================================================================
Server: http://127.0.0.1:8010

核心 Skills:
  🔵 role_definition - 角色定义（always_load）
  ⚪ sqlmap_scanner - SQLMap 扫描（AI 判断加载）

特性:
  ✅ AI 判断加载策略（完全无关键字）
  ✅ Level 3 Resources 支持（脚本、payload）
  ✅ 数据包驱动的 skill 调用
  ✅ 完整的日志记录（prompts.log）
======================================================================
[SkillManager] 已加载 2 个 skills 的元数据
```

---

## 2. 使用方式

### Web 界面

打开浏览器访问：`http://127.0.0.1:8010/web/index.html`

输入数据包：

```
请分析这个数据包是否存在SQL注入：

POST /api/login HTTP/1.1
Host: target.com
Content-Type: application/x-www-form-urlencoded

username=admin&password=test
```

### 命令行

```bash
python router.py "数据包内容..." session1
```

---

## 3. 工作流程

```
Step 1: 用户提供数据包
    ↓
Step 2: AI 分析数据包
    - 识别接口类型（登录、查询、搜索等）
    - 判断可能的漏洞类型
    ↓
Step 3: AI 判断需要的 skill
    - 调用 AI 判断器（~150 tokens）
    - AI 返回: "sqlmap_scanner"
    ↓
Step 4: 加载 sqlmap_scanner skill
    - Level 2: 加载 SKILL.md（指导）
    - Level 3: 检测 resources/（脚本、payload）
    ↓
Step 5: AI 调用 resources 中的工具
    - 使用 sqlmap_wrapper.py
    - 或直接调用 SQLMap
    ↓
Step 6: 返回分析结果
    - 是否存在漏洞
    - 漏洞详情
    - 修复建议
```

---

## 4. 查看日志

### 查看提示词注入

```bash
cat logs/prompts.log
```

你会看到：
- 每次对话注入了哪些内容
- 哪些 skills 被加载
- 完整的 system prompt
- 发送给 AI 的完整 messages

### 查看结构化日志

```bash
cat logs/app.log | tail -1 | python -m json.tool
```

---

## 5. API 使用

### 分析数据包

```bash
curl -X POST http://127.0.0.1:8010/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "请分析这个数据包...",
    "session_id": "user123"
  }'
```

### 获取 skill 资源

```bash
# 列出资源
curl http://127.0.0.1:8010/api/skills/sqlmap_scanner/resources

# 获取脚本内容
curl http://127.0.0.1:8010/api/skills/sqlmap_scanner/resources/sqlmap_wrapper.py
```

---

## 6. Token 消耗

### 第一次对话（加载 sqlmap_scanner）

```
元数据: 200 tokens
role_definition: 150 tokens
sqlmap_scanner: 500 tokens
AI 判断: 150 tokens
────────────────────
总计: ~1000 tokens
```

### 第二次对话（复用）

```
元数据: 200 tokens
历史对话: 100 tokens
────────────────────
总计: ~300 tokens  ✅ 节省 70%
```

---

## 7. 常见场景

### 场景 A：SQL 注入检测

```
用户: [提供登录接口数据包]
AI: 判断需要 sqlmap_scanner → 加载 → 调用 sqlmap_wrapper.py → 返回结果
```

### 场景 B：多个接口测试

```
第1次: [登录接口] → 加载 sqlmap_scanner
第2次: [查询接口] → 复用 sqlmap_scanner ✅
第3次: [搜索接口] → 复用 sqlmap_scanner ✅
```

### 场景 C：简单咨询

```
用户: "什么是SQL注入？"
AI: 判断不需要 sqlmap_scanner → 只用 role_definition → 直接回答
Token: ~300
```

---

## 8. 系统特点

✅ **数据包驱动** - 根据数据包特征调用 skill  
✅ **AI 智能判断** - 零关键字，纯语义理解  
✅ **渐进披露** - 首次加载，后续复用  
✅ **Resources 支持** - 可执行脚本、payload、模板  
✅ **完整日志** - 所有操作可追溯  

---

## 9. 下一步

- 查看 `ARCHITECTURE.md` 了解架构设计
- 查看 `RESOURCES_GUIDE.md` 了解如何添加新资源
- 查看 `LOG_GUIDE.md` 了解日志系统
- 查看 `logs/prompts.log` 查看实际注入的内容





