-- ============================================
-- 数据库迁移脚本
-- 添加 Skill 层级化支持
-- ============================================

-- 添加 level 字段（如果不存在）
-- 1 = 一级技能（可直接加载）
-- 2 = 二级技能（子技能）
ALTER TABLE `skills` ADD COLUMN IF NOT EXISTS `level` INT DEFAULT 1
    COMMENT '技能级别: 1=一级技能(直接可见), 2=二级技能(子技能)';

-- 添加 parent_skill_id 字段（如果不存在）
ALTER TABLE `skills` ADD COLUMN IF NOT EXISTS `parent_skill_id` INT DEFAULT NULL
    COMMENT '父技能ID，NULL表示是一级技能';

-- 添加索引（如果不存在）
-- 注意：MySQL 不支持 IF NOT EXISTS 语法用于索引，需要先检查
-- 这里使用存储过程或忽略错误的方式

-- 尝试添加索引，如果已存在会报错但不影响
-- ALTER TABLE `skills` ADD INDEX `idx_skills_level` (`level`);
-- ALTER TABLE `skills` ADD INDEX `idx_skills_parent` (`parent_skill_id`);

-- 更新现有数据的默认值
UPDATE `skills` SET `level` = 1 WHERE `level` IS NULL;

-- 显示当前表结构
DESCRIBE `skills`;

-- 显示数据
SELECT id, name, level, parent_skill_id, always_load FROM skills;
