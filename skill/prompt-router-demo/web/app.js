/**
 * Anthropic Agent Skills 渐进披露架构 - Web 界面
 * 支持会话管理、skills 可视化和技能管理
 */

(() => {
  // API 配置
  const apiParam = new URLSearchParams(window.location.search).get("api");
  const apiBase = apiParam || "http://127.0.0.1:8010";
  const apiChat = `${apiBase}/api/chat`;
  const apiSkills = `${apiBase}/api/skills`;
  const apiSession = `${apiBase}/api/session`;

  // DOM 元素 - 对话相关
  const statusEl = document.getElementById("status");
  const segmentsEl = document.getElementById("segments");
  const answerEl = document.getElementById("answer");
  const questionEl = document.getElementById("question");
  const sendBtn = document.getElementById("send-btn");
  const clearBtn = document.getElementById("clear-btn");
  const apiUrlEl = document.getElementById("api-url");
  const sessionIdEl = document.getElementById("session-id");
  const newlyLoadedEl = document.getElementById("newly-loaded");
  const skillsListEl = document.getElementById("skills-list");
  const historyEl = document.getElementById("history");

  // DOM 元素 - 技能管理相关
  const addSkillBtn = document.getElementById("add-skill-btn");
  const skillModal = document.getElementById("skill-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalCloseBtn = document.getElementById("modal-close");
  const skillForm = document.getElementById("skill-form");
  const cancelBtn = document.getElementById("cancel-btn");
  const skillIdInput = document.getElementById("skill-id");
  const skillNameInput = document.getElementById("skill-name");
  const skillDescInput = document.getElementById("skill-description");
  const skillInstructionsInput = document.getElementById("skill-instructions");
  const skillAlwaysLoadInput = document.getElementById("skill-always-load");
  const skillVersionInput = document.getElementById("skill-version");

  // DOM 元素 - 确认删除模态框
  const confirmModal = document.getElementById("confirm-modal");
  const deleteSkillNameEl = document.getElementById("delete-skill-name");
  const confirmDeleteBtn = document.getElementById("confirm-delete-btn");

  // DOM 元素 - 标签页和层级相关
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");
  const customSkillsListEl = document.getElementById("custom-skills-list");
  const levelFilter = document.getElementById("level-filter");
  const skillLevelSelect = document.getElementById("skill-level");
  const skillParentSelect = document.getElementById("skill-parent");
  const parentSkillGroup = document.getElementById("parent-skill-group");
  const childSkillHint = document.getElementById("child-skill-hint");

  // 状态
  let currentSessionId = null;
  let conversationHistory = [];
  let availableSkills = [];
  let skillToDelete = null; // 待删除的技能信息
  let currentTab = "available"; // 当前标签页

  // 初始化
  apiUrlEl.textContent = apiBase;
  updateSessionDisplay();

  // 设置状态消息
  const setStatus = (text, isError = false) => {
    statusEl.textContent = text;
    statusEl.classList.toggle("error", isError);
  };

  // 生成新的 session ID
  const generateSessionId = () => {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  };

  // 更新会话显示
  function updateSessionDisplay() {
    if (sessionIdEl) {
      sessionIdEl.textContent = currentSessionId || "未开始";
    }
  }

  // 加载可用的 skills
  async function loadSkills() {
    try {
      const response = await fetch(apiSkills);
      if (!response.ok) {
        console.warn("Failed to load skills metadata");
        return;
      }
      const data = await response.json();
      availableSkills = data.skills || [];
      updateSkillsDisplay();
    } catch (error) {
      console.error("Error loading skills:", error);
    }
  }

  // 更新可用技能列表显示（只显示一级技能）
  function updateSkillsDisplay() {
    if (!skillsListEl) return;

    // 只显示一级技能
    const topLevelSkills = availableSkills.filter(s => s.level === 1 || !s.level);
    const baseSkills = topLevelSkills.filter(s => s.always_load);
    const optionalSkills = topLevelSkills.filter(s => !s.always_load);

    let html = "";

    if (baseSkills.length > 0) {
      html += "<div class='skills-category'>";
      html += "<h4>🔵 核心技能（始终激活）</h4><ul>";
      baseSkills.forEach(skill => {
        const childCount = getChildCount(skill.id);
        const childBadge = childCount > 0 ? `<span class="child-badge" title="${childCount} 个子技能">+${childCount}</span>` : '';
        html += `<li data-skill="${skill.name}" data-skill-id="${skill.id}">
          <div class="skill-info">
            <strong>${skill.name}</strong>${childBadge}: ${skill.description}
          </div>
        </li>`;
      });
      html += "</ul></div>";
    }

    if (optionalSkills.length > 0) {
      html += "<div class='skills-category'>";
      html += "<h4>⚪ 专业技能（按需激活）</h4><ul>";
      optionalSkills.forEach(skill => {
        const childCount = getChildCount(skill.id);
        const childBadge = childCount > 0 ? `<span class="child-badge" title="${childCount} 个子技能">+${childCount}</span>` : '';
        html += `<li data-skill="${skill.name}" data-skill-id="${skill.id}" class="optional-skill">
          <div class="skill-info">
            <strong>${skill.name}</strong>${childBadge}: ${skill.description}
          </div>
        </li>`;
      });
      html += "</ul></div>";
    }

    skillsListEl.innerHTML = html || "<p>无可用技能</p>";
  }

  // 获取技能的子技能数量
  function getChildCount(parentId) {
    return availableSkills.filter(s => s.parent_skill_id === parentId).length;
  }

  // 更新技能管理页面（树形结构）
  function updateCustomSkillsDisplay(filterLevel = "all") {
    if (!customSkillsListEl) return;

    let filteredSkills = availableSkills;
    if (filterLevel !== "all") {
      filteredSkills = availableSkills.filter(s => s.level === parseInt(filterLevel));
    }

    // 构建树形结构
    const topLevel = filteredSkills.filter(s => s.level === 1 || !s.level);
    const childSkills = filteredSkills.filter(s => s.level > 1);

    let html = "";

    if (topLevel.length === 0 && childSkills.length === 0) {
      html = "<p>暂无技能，点击上方按钮创建</p>";
    } else {
      html = "<ul class='skill-tree'>";

      // 显示一级技能及其子技能
      topLevel.forEach(skill => {
        const children = availableSkills.filter(s => s.parent_skill_id === skill.id);
        const levelTag = `<span class="level-tag level-1">L1</span>`;
        const alwaysLoadTag = skill.always_load ? '<span class="tag-always">核心</span>' : '';

        html += `<li class="tree-item level-1-item" data-skill-id="${skill.id}">
          <div class="tree-node">
            <div class="skill-info">
              ${levelTag}${alwaysLoadTag}
              <strong>${skill.name}</strong>
              <span class="skill-desc">: ${skill.description}</span>
            </div>
            <div class="skill-actions">
              <button class="btn-icon btn-edit" onclick="window.editSkill(${skill.id})" title="编辑">✏️</button>
              <button class="btn-icon btn-delete" onclick="window.deleteSkill(${skill.id}, '${skill.name}')" title="删除">🗑️</button>
            </div>
          </div>`;

        // 显示子技能
        if (children.length > 0) {
          html += `<ul class="skill-children">`;
          children.forEach(child => {
            const childLevelTag = `<span class="level-tag level-2">L${child.level}</span>`;
            html += `<li class="tree-item level-2-item" data-skill-id="${child.id}">
              <div class="tree-node child-node">
                <div class="skill-info">
                  ${childLevelTag}
                  <strong>${child.name}</strong>
                  <span class="skill-desc">: ${child.description}</span>
                </div>
                <div class="skill-actions">
                  <button class="btn-icon btn-edit" onclick="window.editSkill(${child.id})" title="编辑">✏️</button>
                  <button class="btn-icon btn-delete" onclick="window.deleteSkill(${child.id}, '${child.name}')" title="删除">🗑️</button>
                </div>
              </div>
            </li>`;
          });
          html += `</ul>`;
        }

        html += `</li>`;
      });

      // 显示孤立的子技能（筛选为子技能时）
      if (filterLevel === "2") {
        childSkills.forEach(skill => {
          const parentSkill = availableSkills.find(s => s.id === skill.parent_skill_id);
          const parentName = parentSkill ? parentSkill.name : '未知';
          const levelTag = `<span class="level-tag level-2">L${skill.level}</span>`;

          html += `<li class="tree-item level-2-item" data-skill-id="${skill.id}">
            <div class="tree-node">
              <div class="skill-info">
                ${levelTag}
                <strong>${skill.name}</strong>
                <span class="skill-desc">: ${skill.description}</span>
                <span class="parent-ref">← ${parentName}</span>
              </div>
              <div class="skill-actions">
                <button class="btn-icon btn-edit" onclick="window.editSkill(${skill.id})" title="编辑">✏️</button>
                <button class="btn-icon btn-delete" onclick="window.deleteSkill(${skill.id}, '${skill.name}')" title="删除">🗑️</button>
              </div>
            </div>
          </li>`;
        });
      }

      html += "</ul>";
    }

    customSkillsListEl.innerHTML = html;
  }

  // 更新父技能下拉框选项
  function updateParentSkillOptions() {
    if (!skillParentSelect) return;

    const topLevelSkills = availableSkills.filter(s => s.level === 1 || !s.level);

    let options = '<option value="">-- 选择父技能 --</option>';
    topLevelSkills.forEach(skill => {
      options += `<option value="${skill.id}">${skill.name}</option>`;
    });

    skillParentSelect.innerHTML = options;
  }

  // 切换标签页
  function switchTab(tabName) {
    currentTab = tabName;

    tabBtns.forEach(btn => {
      btn.classList.toggle("active", btn.dataset.tab === tabName);
    });

    tabContents.forEach(content => {
      content.classList.toggle("active", content.id === `tab-${tabName}`);
    });

    if (tabName === "custom") {
      updateCustomSkillsDisplay(levelFilter ? levelFilter.value : "all");
    }
  }

  // 高亮新激活的 skills
  function highlightNewSkills(skillNames) {
    if (!skillsListEl || !skillNames || skillNames.length === 0) return;

    skillNames.forEach(name => {
      const skillEl = skillsListEl.querySelector(`[data-skill="${name}"]`);
      if (skillEl) {
        skillEl.classList.add("active-skill");
        setTimeout(() => {
          skillEl.classList.remove("active-skill");
        }, 3000);
      }
    });
  }

  // 更新对话历史显示
  function updateHistoryDisplay() {
    if (!historyEl) return;

    if (conversationHistory.length === 0) {
      historyEl.innerHTML = "<p>暂无历史记录</p>";
      return;
    }

    let html = "<ul>";
    conversationHistory.forEach((msg, index) => {
      const isUser = msg.role === "user";
      const icon = isUser ? "👤" : "🤖";
      const preview = msg.content.substring(0, 50) + (msg.content.length > 50 ? "..." : "");
      html += `<li class="${msg.role}">
        <span class="icon">${icon}</span>
        <span class="preview">${preview}</span>
      </li>`;
    });
    html += "</ul>";
    
    historyEl.innerHTML = html;
  }

  // 发送问题
  const sendQuestion = async () => {
    const question = questionEl.value.trim();
    if (!question) {
      setStatus("请输入问题", true);
      return;
    }

    // 如果没有 session，创建一个
    if (!currentSessionId) {
      currentSessionId = generateSessionId();
      updateSessionDisplay();
      console.log("Created new session:", currentSessionId);
    }

    setStatus("⏳ 请求中...");
    answerEl.textContent = "AI 正在思考...";
    segmentsEl.textContent = "-";
    if (newlyLoadedEl) newlyLoadedEl.textContent = "-";
    sendBtn.disabled = true;

    // 添加到历史
    conversationHistory.push({ role: "user", content: question });
    updateHistoryDisplay();

    try {
      const response = await fetch(apiChat, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          question,
          session_id: currentSessionId 
        }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || "请求失败");
      }

      // 更新 session ID
      if (data.session_id) {
        currentSessionId = data.session_id;
        updateSessionDisplay();
      }

      // 显示结果
      const skills = data.skills || [];
      const newlyLoaded = data.newly_loaded_skills || [];
      
      segmentsEl.textContent = skills.join(", ") || "-";
      
      if (newlyLoadedEl) {
        if (newlyLoaded.length > 0) {
          newlyLoadedEl.textContent = `🆕 ${newlyLoaded.join(", ")}`;
          newlyLoadedEl.style.color = "#4CAF50";
          highlightNewSkills(newlyLoaded);
        } else if (skills.length > 0) {
          newlyLoadedEl.textContent = "✅ 复用已加载的技能";
          newlyLoadedEl.style.color = "#2196F3";
        } else {
          newlyLoadedEl.textContent = "-";
        }
      }
      
      answerEl.textContent = data.answer || "";
      setStatus("✅ 完成");

      // 添加到历史
      conversationHistory.push({ role: "assistant", content: data.answer });
      updateHistoryDisplay();

      // 清空输入
      questionEl.value = "";
      questionEl.focus();

    } catch (error) {
      answerEl.textContent = `❌ 错误: ${error.message}`;
      setStatus(error.message || "请求失败", true);
    } finally {
      sendBtn.disabled = false;
    }
  };

  // 清除会话
  const clearSession = async () => {
    if (!confirm("确定要清除当前会话吗？这将重置所有已加载的技能。")) {
      return;
    }

    // 如果有当前会话，清除服务端状态
    if (currentSessionId) {
      try {
        await fetch(`${apiSession}/${currentSessionId}`, {
          method: "DELETE"
        });
        console.log("Session cleared on server:", currentSessionId);
      } catch (error) {
        console.error("Failed to clear session:", error);
      }
    }

    // 重置客户端状态
    currentSessionId = null;
    conversationHistory = [];
    updateSessionDisplay();
    updateHistoryDisplay();
    
    // 重置显示
    answerEl.textContent = "";
    segmentsEl.textContent = "-";
    if (newlyLoadedEl) newlyLoadedEl.textContent = "-";
    questionEl.value = "";
    
    // 移除所有高亮
    if (skillsListEl) {
      const skillEls = skillsListEl.querySelectorAll("li");
      skillEls.forEach(el => el.classList.remove("active-skill"));
    }
    
    setStatus("✨ 会话已清除，开始新对话");
  };

  // ==================== 技能管理功能 ====================

  // 处理级别切换
  function handleLevelChange() {
    const level = parseInt(skillLevelSelect.value);

    if (parentSkillGroup) {
      parentSkillGroup.style.display = level > 1 ? "block" : "none";
    }

    // 二级技能不能设为"始终加载"
    if (skillAlwaysLoadInput) {
      if (level > 1) {
        skillAlwaysLoadInput.checked = false;
        skillAlwaysLoadInput.disabled = true;
      } else {
        skillAlwaysLoadInput.disabled = false;
      }
    }

    // 显示/隐藏子技能引用提示
    if (childSkillHint) {
      childSkillHint.style.display = level === 1 ? "block" : "none";
    }
  }

  // 打开新建技能模态框
  function openCreateModal() {
    modalTitle.textContent = "新建技能";
    skillForm.reset();
    skillIdInput.value = "";
    skillVersionInput.value = "1.0.0";

    // 重置级别相关
    if (skillLevelSelect) {
      skillLevelSelect.value = "1";
      handleLevelChange();
    }

    // 更新父技能选项
    updateParentSkillOptions();

    skillModal.classList.add("active");
    skillNameInput.focus();
  }

  // 打开编辑技能模态框
  async function openEditModal(skillId) {
    try {
      const response = await fetch(`${apiSkills}/${skillId}`);
      if (!response.ok) {
        throw new Error("获取技能详情失败");
      }
      const skill = await response.json();

      modalTitle.textContent = "编辑技能";
      skillIdInput.value = skill.id;
      skillNameInput.value = skill.name;
      skillDescInput.value = skill.description;
      skillInstructionsInput.value = skill.instructions;
      skillAlwaysLoadInput.checked = skill.always_load;
      skillVersionInput.value = skill.version || "1.0.0";

      // 设置级别
      if (skillLevelSelect) {
        skillLevelSelect.value = skill.level || 1;
        handleLevelChange();
      }

      // 更新并设置父技能
      updateParentSkillOptions();
      if (skillParentSelect && skill.parent_skill_id) {
        skillParentSelect.value = skill.parent_skill_id;
      }

      skillModal.classList.add("active");
      skillNameInput.focus();
    } catch (error) {
      alert("加载技能详情失败: " + error.message);
    }
  }

  // 关闭技能模态框
  function closeSkillModal() {
    skillModal.classList.remove("active");
  }

  // 保存技能（创建或更新）
  async function saveSkill(e) {
    e.preventDefault();

    const skillId = skillIdInput.value;
    const isEdit = !!skillId;

    const level = skillLevelSelect ? parseInt(skillLevelSelect.value) : 1;
    const parentSkillId = (level > 1 && skillParentSelect) ? parseInt(skillParentSelect.value) || null : null;

    // 验证二级技能必须有父技能
    if (level > 1 && !parentSkillId) {
      alert("二级技能必须选择一个父技能");
      return;
    }

    const skillData = {
      name: skillNameInput.value.trim(),
      description: skillDescInput.value.trim(),
      instructions: skillInstructionsInput.value.trim(),
      always_load: level === 1 ? skillAlwaysLoadInput.checked : false,
      version: skillVersionInput.value.trim() || "1.0.0",
      enabled: true,
      level: level,
      parent_skill_id: parentSkillId
    };

    // 验证必填字段
    if (!skillData.name || !skillData.description || !skillData.instructions) {
      alert("请填写所有必填字段");
      return;
    }

    try {
      const url = isEdit ? `${apiSkills}/${skillId}` : apiSkills;
      const method = isEdit ? "PUT" : "POST";

      const response = await fetch(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(skillData)
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "保存失败");
      }

      closeSkillModal();
      await loadSkills(); // 重新加载技能列表
      setStatus(`✅ 技能 "${skillData.name}" ${isEdit ? "更新" : "创建"}成功`);
    } catch (error) {
      alert("保存技能失败: " + error.message);
    }
  }

  // 打开删除确认模态框
  function openDeleteConfirm(skillId, skillName) {
    skillToDelete = { id: skillId, name: skillName };
    deleteSkillNameEl.textContent = skillName;
    confirmModal.classList.add("active");
  }

  // 关闭删除确认模态框
  function closeConfirmModal() {
    confirmModal.classList.remove("active");
    skillToDelete = null;
  }

  // 确认删除技能
  async function confirmDelete() {
    if (!skillToDelete) return;

    try {
      const response = await fetch(`${apiSkills}/${skillToDelete.id}`, {
        method: "DELETE"
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "删除失败");
      }

      closeConfirmModal();
      await loadSkills(); // 重新加载技能列表
      setStatus(`✅ 技能 "${skillToDelete.name}" 已删除`);
    } catch (error) {
      alert("删除技能失败: " + error.message);
    }
  }

  // 暴露给全局，供 onclick 使用
  window.editSkill = openEditModal;
  window.deleteSkill = openDeleteConfirm;

  // ==================== 事件监听 ====================

  // 对话相关
  sendBtn.addEventListener("click", sendQuestion);
  if (clearBtn) {
    clearBtn.addEventListener("click", clearSession);
  }

  questionEl.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  });

  // 标签页切换
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      switchTab(btn.dataset.tab);
    });
  });

  // 级别筛选
  if (levelFilter) {
    levelFilter.addEventListener("change", () => {
      updateCustomSkillsDisplay(levelFilter.value);
    });
  }

  // 级别选择变化
  if (skillLevelSelect) {
    skillLevelSelect.addEventListener("change", handleLevelChange);
  }

  // 技能管理相关
  if (addSkillBtn) {
    addSkillBtn.addEventListener("click", openCreateModal);
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeSkillModal);
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", closeSkillModal);
  }

  if (skillForm) {
    skillForm.addEventListener("submit", saveSkill);
  }

  // 确认删除模态框
  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener("click", confirmDelete);
  }

  // 关闭确认模态框的按钮们
  document.querySelectorAll(".confirm-close").forEach(btn => {
    btn.addEventListener("click", closeConfirmModal);
  });

  // 点击模态框背景关闭
  if (skillModal) {
    skillModal.addEventListener("click", (e) => {
      if (e.target === skillModal) {
        closeSkillModal();
      }
    });
  }

  if (confirmModal) {
    confirmModal.addEventListener("click", (e) => {
      if (e.target === confirmModal) {
        closeConfirmModal();
      }
    });
  }

  // ESC 键关闭模态框
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeSkillModal();
      closeConfirmModal();
    }
  });

  // 初始化：加载 skills
  loadSkills();
  setStatus("✨ 就绪 - 渐进披露模式已启用");
})();
