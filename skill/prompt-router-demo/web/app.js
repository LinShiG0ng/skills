/**
 * Anthropic Agent Skills 渐进披露架构 - Web 界面
 * 支持会话管理和 skills 可视化
 */

(() => {
  // API 配置
  const apiParam = new URLSearchParams(window.location.search).get("api");
  const apiBase = apiParam || "http://127.0.0.1:8010";
  const apiChat = `${apiBase}/api/chat`;
  const apiSkills = `${apiBase}/api/skills`;
  const apiSession = `${apiBase}/api/session`;

  // DOM 元素
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

  // 状态
  let currentSessionId = null;
  let conversationHistory = [];
  let availableSkills = [];

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
        html += `<li data-skill="${skill.name}">
          <strong>${skill.name}</strong>: ${skill.description}
        </li>`;
      });
      html += "</ul></div>";
    }

    if (optionalSkills.length > 0) {
      html += "<div class='skills-category'>";
      html += "<h4>⚪ 专业技能（按需激活）</h4><ul>";
      optionalSkills.forEach(skill => {
        html += `<li data-skill="${skill.name}" class="optional-skill">
          <strong>${skill.name}</strong>: ${skill.description}
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

  // 事件监听
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

  // 初始化：加载 skills
  loadSkills();
  setStatus("✨ 就绪 - 渐进披露模式已启用");
})();
