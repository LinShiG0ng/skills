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

  // 状态
  let currentSessionId = null;
  let conversationHistory = [];
  let availableSkills = [];
  let skillToDelete = null; // 待删除的技能信息

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

  // 更新 skills 列表显示
  function updateSkillsDisplay() {
    if (!skillsListEl) return;

    const baseSkills = availableSkills.filter(s => s.always_load);
    const optionalSkills = availableSkills.filter(s => !s.always_load);

    let html = "";

    if (baseSkills.length > 0) {
      html += "<div class='skills-category'>";
      html += "<h4>🔵 核心技能（始终激活）</h4><ul>";
      baseSkills.forEach(skill => {
        html += `<li data-skill="${skill.name}" data-skill-id="${skill.id}">
          <div class="skill-info">
            <strong>${skill.name}</strong>: ${skill.description}
          </div>
          <div class="skill-actions">
            <button class="btn-icon btn-edit" onclick="window.editSkill(${skill.id})" title="编辑">✏️</button>
            <button class="btn-icon btn-delete" onclick="window.deleteSkill(${skill.id}, '${skill.name}')" title="删除">🗑️</button>
          </div>
        </li>`;
      });
      html += "</ul></div>";
    }

    if (optionalSkills.length > 0) {
      html += "<div class='skills-category'>";
      html += "<h4>⚪ 专业技能（按需激活）</h4><ul>";
      optionalSkills.forEach(skill => {
        html += `<li data-skill="${skill.name}" data-skill-id="${skill.id}" class="optional-skill">
          <div class="skill-info">
            <strong>${skill.name}</strong>: ${skill.description}
          </div>
          <div class="skill-actions">
            <button class="btn-icon btn-edit" onclick="window.editSkill(${skill.id})" title="编辑">✏️</button>
            <button class="btn-icon btn-delete" onclick="window.deleteSkill(${skill.id}, '${skill.name}')" title="删除">🗑️</button>
          </div>
        </li>`;
      });
      html += "</ul></div>";
    }

    skillsListEl.innerHTML = html || "<p>无可用技能</p>";
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

  // 打开新建技能模态框
  function openCreateModal() {
    modalTitle.textContent = "新建技能";
    skillForm.reset();
    skillIdInput.value = "";
    skillVersionInput.value = "1.0.0";
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

    const skillData = {
      name: skillNameInput.value.trim(),
      description: skillDescInput.value.trim(),
      instructions: skillInstructionsInput.value.trim(),
      always_load: skillAlwaysLoadInput.checked,
      version: skillVersionInput.value.trim() || "1.0.0",
      enabled: true
    };

    // 验证
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
