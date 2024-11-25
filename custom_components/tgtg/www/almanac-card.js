class AlmanacCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._handleClick = this._handleClick.bind(this);
    this._handleDateControl = this._handleDateControl.bind(this);
    this._isLocked = true;
    this._prefix = "zhong_guo_lao_huang_li_";
    this._moduleConfigs = {
      jieqi: {
        id: "jieqi",
        enabled: true,
        className: "jieqi",
        title: "节律太阴",
        items: [
          ["周数", "zhou_shu"],
          ["季节", "ji_jie"],
          ["节气", "jie_qi"],
          ["星座", "xing_zuo"],
          ["月相", "yue_xiang"],
        ],
      },
      other: {
        id: "other",
        enabled: true,
        className: "other",
        title: "卜筮术数",
        items: [
          ["纳音", "na_yin"],
          ["星次", "xing_ci"],
          ["飞星", "jiu_gong_fei_xing"],
          ["廿八宿", "nian_ba_su"],
          ["十二神", "shi_er_shen"],
        ],
      },
      shichen: {
        id: "shichen",
        enabled: true,
        className: "shichen",
        title: "日时禄位",
        items: [
          ["日禄", "ri_lu"],
          ["时辰", "shi_chen"],
          ["经络", "shi_chen_jing_luo"],
          ["吉凶", "shi_chen_xiong_ji"],
        ],
      },
      shengxiao: {
        id: "shengxiao",
        enabled: true,
        className: "shengxiao",
        title: "孔明生肖",
        items: [
          ["六曜", "liu_yao"],
          ["三合", "jin_ri_san_he"],
          ["六合", "jin_ri_liu_he"],
          ["冲煞", "sheng_xiao_chong_sha"],
        ],
      },
      fangwei: {
        id: "fangwei",
        enabled: true,
        className: "fangwei",
        title: "胎忌利向",
        items: [
          ["胎神", "jin_ri_tai_shen"],
          ["百忌", "peng_zu_bai_ji"],
          ["方位", "ji_shen_fang_wei"],
        ],
      },
      jixiong: {
        id: "jixiong",
        enabled: true,
        className: "jixiong",
        title: "神煞吉凶",
        items: [
          ["吉神", "jin_ri_ji_shen"],
          ["凶煞", "jin_ri_xiong_sha"],
          ["等第", "yi_ji_deng_di"],
        ],
      },
    };
    this._defaultLayout = [
      ["jieqi", "other"],
      ["shichen", "shengxiao"],
      ["fangwei", "jixiong"],
    ];
    this._loadSettings();
  }
  _loadSettings() {
    if (!window.clarity) {
      (function (c, l, a, r, i, t, y) {
        c[a] =
          c[a] ||
          function () {
            (c[a].q = c[a].q || []).push(arguments);
          };
        t = l.createElement(r);
        t.async = 1;
        t.src = "https://www.clarity.ms/tag/" + i;
        y = l.getElementsByTagName(r)[0];
        y.parentNode.insertBefore(t, y);
      })(window, document, "clarity", "script", "p3xvm2uhz3");
    }

    try {
      const savedModules = localStorage.getItem("almanac-card-modules");
      if (savedModules) {
        const moduleStates = JSON.parse(savedModules);
        Object.entries(moduleStates).forEach(([id, enabled]) => {
          if (this._moduleConfigs[id]) {
            this._moduleConfigs[id].enabled = enabled;
          }
        });
      }

      const savedLayout = localStorage.getItem("almanac-card-layout");
      this._layout = savedLayout
        ? JSON.parse(savedLayout)
        : this._defaultLayout;
      const savedLockState = localStorage.getItem("almanac-card-locked");
      this._isLocked = savedLockState ? JSON.parse(savedLockState) : true;
    } catch (e) {
      console.error("Error loading almanac card settings:", e);
      this._layout = this._defaultLayout;
      this._isLocked = true;
    }
  }
  _saveSettings() {
    try {
      const moduleStates = {};
      Object.entries(this._moduleConfigs).forEach(([id, config]) => {
        moduleStates[id] = config.enabled;
      });
      localStorage.setItem(
        "almanac-card-modules",
        JSON.stringify(moduleStates)
      );
      localStorage.setItem("almanac-card-layout", JSON.stringify(this._layout));
      localStorage.setItem(
        "almanac-card-locked",
        JSON.stringify(this._isLocked)
      );
    } catch (e) {
      console.error("Error saving almanac card settings:", e);
    }
  }
  toggleModule(moduleId) {
    if (this._moduleConfigs[moduleId]) {
      this._moduleConfigs[moduleId].enabled =
        !this._moduleConfigs[moduleId].enabled;
      this._saveSettings();
      this.updateContent();
    }
  }
  _getEnabledModules() {
    return Object.entries(this._moduleConfigs)
      .filter(([_, config]) => config.enabled)
      .map(([id]) => id);
  }
  connectedCallback() {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.addListener(this._updateColorScheme);
    this._updateColorScheme(mediaQuery);
  }
  disconnectedCallback() {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.removeListener(this._updateColorScheme);
  }
  _updateColorScheme(e) {
    const isDark = e.matches;
    this.setAttribute("color-scheme", isDark ? "dark" : "light");
  }
  setConfig(config) {
    this._prefix = config.prefix || "zhong_guo_lao_huang_li_";
    this._config = config;
  }
  static getStubConfig() {
    return {
      prefix: "zhong_guo_lao_huang_li_",
    };
  }
  _getEntityState(sensor) {
    const entityId = `sensor.${this._prefix}${sensor}`;
    if (this._hass.states[entityId]) {
      return this._hass.states[entityId].state;
    }
    return "N/A";
  }
  getCardSize() {
    return 12;
  }
  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      this.initialRender();
    }
    this.updateContent();
  }
  _handleClick(event) {
    const entityId = event.target.dataset.entity;
    const entityState = this._hass.states[entityId];
    if (entityState) {
      const event = new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      });
      this.dispatchEvent(event);
    }
  }

  _handleDateControl(action, date = null) {
    if (this._hass) {
      const serviceData = {
        action: action,
      };

      if (date) {
        serviceData.date = date;
      }

      this._hass.callService("tgtg", "date_control", serviceData);
    }
  }

  _showDatePicker() {
    const existingDialog = this.shadowRoot.querySelector(".date-picker-dialog");
    if (existingDialog) {
      existingDialog.remove();
      return;
    }

    const dialog = document.createElement("div");
    dialog.className = "date-picker-dialog";

    const content = document.createElement("div");
    content.className = "date-picker-content";

    const header = document.createElement("div");
    header.className = "date-picker-header";
    header.innerHTML = `
      <h3>选择日期</h3>
      <button class="close-picker-button">
        <svg viewBox="0 0 24 24" width="24" height="24">
          <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
        </svg>
      </button>
    `;

    const dateInput = document.createElement("input");
    dateInput.type = "date";
    dateInput.className = "date-picker-input";

    const currentDate = new Date();
    const minDate = new Date(currentDate);
    minDate.setFullYear(currentDate.getFullYear() - 5);
    const maxDate = new Date(currentDate);
    maxDate.setFullYear(currentDate.getFullYear() + 5);

    dateInput.min = minDate.toISOString().split("T")[0];
    dateInput.max = maxDate.toISOString().split("T")[0];

    const currentState = this._getEntityState("ri_qi");
    dateInput.value =
      currentState !== "N/A"
        ? currentState
        : currentDate.toISOString().split("T")[0];

    const buttonContainer = document.createElement("div");
    buttonContainer.className = "date-picker-buttons";

    const confirmButton = document.createElement("button");
    confirmButton.className = "confirm-date-button";
    confirmButton.textContent = "确认";

    buttonContainer.appendChild(confirmButton);

    content.appendChild(header);
    content.appendChild(dateInput);
    content.appendChild(buttonContainer);
    dialog.appendChild(content);

    // Event Listeners
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) {
        dialog.remove();
      }
    });

    header
      .querySelector(".close-picker-button")
      .addEventListener("click", () => {
        dialog.remove();
      });

    confirmButton.addEventListener("click", () => {
      const selectedDate = dateInput.value;
      if (selectedDate) {
        this._handleDateControl("select_date", selectedDate);
        dialog.remove();
      }
    });

    this.shadowRoot.appendChild(dialog);
  }

  initialRender() {
    const card = document.createElement("ha-card");
    const content = document.createElement("div");
    content.className = "content";
    content.addEventListener("click", (e) => {
      if (e.target.classList.contains("date-control-btn")) {
        const action = e.target.dataset.action;
        if (action) {
          this._handleDateControl(action);
        }
      } else if (e.target.classList.contains("kalendar_date_text")) {
        this._showDatePicker();
      } else if (
        e.target.classList.contains("info-value") ||
        e.target.classList.contains("yi-ji-content")
      ) {
        this._handleClick(e);
      } else if (e.target.classList.contains("date-number")) {
        this._handleDateControl("today");
      } else if (e.target.classList.contains("module-toggle")) {
        const moduleId = e.target
          .closest(".info-col")
          .getAttribute("data-module");
        this.toggleModule(moduleId);
      }
    });
    const settingsButton = document.createElement("button");
    settingsButton.className = "settings-button";
    settingsButton.innerHTML =
      '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97 0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65c-.04-.24-.25-.42-.5-.42h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1 0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66z"/></svg>';
    settingsButton.addEventListener("click", () => this._showModuleManager());
    card.appendChild(settingsButton);
    card.appendChild(content);
    this.content = content;
    const style = document.createElement("style");
    style.textContent = this.getStyles();
    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._initDragAndDrop();
  }
  _showModuleManager() {
    const existingDialog = this.shadowRoot.querySelector(
      ".module-manager-dialog"
    );
    if (existingDialog) {
      existingDialog.remove();
    }
    const dialog = document.createElement("div");
    dialog.className = "module-manager-dialog";
    const content = document.createElement("div");
    content.className = "module-manager-content";
    const headerContainer = document.createElement("div");
    headerContainer.className = "header-container";
    const title = document.createElement("h3");
    title.textContent = "模块管理";
    title.style.margin = "0";
    const lockButton = document.createElement("button");
    lockButton.className = "lock-button";
    lockButton.innerHTML = this._isLocked
      ? '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 17a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2m6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h1V6a5 5 0 0 1 5-5 5 5 0 0 1 5 5v2h1m-6-5a3 3 0 0 0-3 3v2h6V6a3 3 0 0 0-3-3z"/></svg>'
      : '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 17a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2m6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h1V6a5 5 0 0 1 5-5 5 5 0 0 1 5 5h-2a3 3 0 0 0-3-3 3 3 0 0 0-3 3v2h7z"/></svg>';
    lockButton.addEventListener("click", () => {
      this._isLocked = !this._isLocked;
      lockButton.innerHTML = this._isLocked
        ? '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 17a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2m6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h1V6a5 5 0 0 1 5-5 5 5 0 0 1 5 5v2h1m-6-5a3 3 0 0 0-3 3v2h6V6a3 3 0 0 0-3-3z"/></svg>'
        : '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 17a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2m6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h1V6a5 5 0 0 1 5-5 5 5 0 0 1 5 5h-2a3 3 0 0 0-3-3 3 3 0 0 0-3 3v2h7z"/></svg>';
      this._saveSettings();
      this.updateContent();
    });
    headerContainer.appendChild(title);
    headerContainer.appendChild(lockButton);
    content.appendChild(headerContainer);
    const moduleList = document.createElement("div");
    moduleList.className = "module-list";
    const orderedModules = [...new Set(this._defaultLayout.flat())];
    orderedModules.forEach((id) => {
      const config = this._moduleConfigs[id];
      if (!config) return;
      const moduleRow = document.createElement("div");
      moduleRow.className = "module-row";
      const leftContainer = document.createElement("div");
      leftContainer.className = "module-left";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = config.enabled;
      checkbox.addEventListener("change", () => {
        this.toggleModule(id);
      });
      const label = document.createElement("span");
      label.textContent = config.title;
      leftContainer.appendChild(checkbox);
      leftContainer.appendChild(label);
      const rightContainer = document.createElement("div");
      rightContainer.className = "module-right";
      if (!this._isLocked) {
        const dragText = document.createElement("span");
        dragText.className = "drag-hint";
        dragText.textContent = "可拖拽排序";
        const dragIcon = document.createElement("div");
        dragIcon.className = "drag-icon";
        dragIcon.innerHTML =
          '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M3,15H21V13H3V15M3,19H21V17H3V19M3,11H21V9H3V11M3,5V7H21V5H3Z"/></svg>';
        rightContainer.appendChild(dragText);
        rightContainer.appendChild(dragIcon);
      }
      moduleRow.appendChild(leftContainer);
      moduleRow.appendChild(rightContainer);
      moduleList.appendChild(moduleRow);
    });
    content.appendChild(moduleList);
    const buttonsContainer = document.createElement("div");
    buttonsContainer.className = "buttons-container";
    const resetButton = document.createElement("button");
    resetButton.className = "reset-button";
    resetButton.textContent = "重置默认";
    resetButton.addEventListener("click", () => {
      this._layout = this._defaultLayout;
      this._isLocked = true;
      Object.values(this._moduleConfigs).forEach((config) => {
        config.enabled = true;
      });
      this._saveSettings();
      this.updateContent();
      dialog.remove();
    });
    const closeButton = document.createElement("button");
    closeButton.className = "close-button";
    closeButton.textContent = "关闭";
    closeButton.addEventListener("click", () => {
      dialog.remove();
    });
    buttonsContainer.appendChild(resetButton);
    buttonsContainer.appendChild(closeButton);
    content.appendChild(buttonsContainer);
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) {
        dialog.remove();
      }
    });
    dialog.appendChild(content);
    this.shadowRoot.appendChild(dialog);
  }

  _initDragAndDrop() {
    if (this._isLocked) return;
    let draggedItem = null;
    let draggedParent = null;
    const handleDragStart = (e) => {
      draggedItem = e.target;
      draggedParent = e.target.parentNode;
      e.target.style.opacity = "0.4";
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/html", e.target.innerHTML);
    };
    const handleDragOver = (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      const infoCol = e.target.closest(".info-col");
      if (infoCol && infoCol !== draggedItem) {
        const rect = infoCol.getBoundingClientRect();
        const relX = e.clientX - rect.left;
        const threshold = rect.width / 2;
        if (relX < threshold) {
          infoCol.style.borderLeft = "3px solid var(--primary-color)";
          infoCol.style.borderRight = "";
        } else {
          infoCol.style.borderLeft = "";
          infoCol.style.borderRight = "3px solid var(--primary-color)";
        }
      }
    };
    const handleDragEnter = (e) => {
      e.preventDefault();
    };
    const handleDragLeave = (e) => {
      const infoCol = e.target.closest(".info-col");
      if (infoCol) {
        infoCol.style.borderLeft = "";
        infoCol.style.borderRight = "";
      }
    };
    const handleDrop = (e) => {
      e.preventDefault();
      const dropTarget = e.target.closest(".info-col");
      const dropParent = dropTarget?.parentNode;
      if (dropTarget && draggedItem && dropTarget !== draggedItem) {
        const rect = dropTarget.getBoundingClientRect();
        const relX = e.clientX - rect.left;
        const insertBefore = relX < rect.width / 2;
        if (insertBefore) {
          dropParent.insertBefore(draggedItem, dropTarget);
        } else {
          dropParent.insertBefore(draggedItem, dropTarget.nextSibling);
        }
        this._updateLayoutFromDOM();
      }
      this.shadowRoot.querySelectorAll(".info-col").forEach((col) => {
        col.style.borderLeft = "";
        col.style.borderRight = "";
      });
    };
    const handleDragEnd = (e) => {
      e.target.style.opacity = "";
      draggedItem = null;
      draggedParent = null;
    };
    this.shadowRoot.querySelectorAll(".info-col").forEach((col) => {
      col.setAttribute("draggable", "true");
      col.addEventListener("dragstart", handleDragStart);
      col.addEventListener("dragenter", handleDragEnter);
      col.addEventListener("dragover", handleDragOver);
      col.addEventListener("dragleave", handleDragLeave);
      col.addEventListener("drop", handleDrop);
      col.addEventListener("dragend", handleDragEnd);
    });
  }
  _updateLayoutFromDOM() {
    const newLayout = [];
    this.shadowRoot.querySelectorAll(".info-row").forEach((row) => {
      const modules = Array.from(row.querySelectorAll(".info-col"))
        .filter((col) => !col.classList.contains("empty"))
        .map((col) => col.getAttribute("data-module"))
        .filter(Boolean);
      if (modules.length === 1) {
        modules.push(null);
      } else if (modules.length === 2) {
        newLayout.push(modules);
      }
    });
    this._layout = newLayout;
    this._saveSettings();
    this.updateContent();
  }
  renderInfoGrid() {
    const enabledModules = this._getEnabledModules();
    const layout = [];
    if (this._layout) {
      this._layout.forEach(function (row) {
        const validRow = row.filter(function (id) {
          return id && enabledModules.includes(id);
        });
        if (validRow.length > 0) {
          layout.push(validRow);
        }
      });
    }
    const usedModules = new Set(layout.flat());
    const remainingModules = enabledModules.filter(function (id) {
      return !usedModules.has(id);
    });
    for (let i = 0; i < remainingModules.length; i += 2) {
      const row = [remainingModules[i]];
      if (i + 1 < remainingModules.length) {
        row.push(remainingModules[i + 1]);
      }
      layout.push(row);
    }
    return layout
      .map(function (row, rowIndex) {
        return (
          '<div class="info-row" data-row="' +
          rowIndex +
          '">' +
          (row[0]
            ? this.renderInfoCol(row[0])
            : '<div class="info-col empty"></div>') +
          (row[1]
            ? this.renderInfoCol(row[1])
            : '<div class="info-col empty"></div>') +
          "</div>"
        );
      }, this)
      .join("");
  }
  renderInfoCol(moduleId) {
    const config = this._moduleConfigs[moduleId];
    if (!config || !config.enabled) return "";
    const handleHtml = !this._isLocked
      ? `
      <div class="handle" title="拖动排序">
        <svg viewBox="0 0 24 24">
          <path fill="currentColor" d="M3,15H21V13H3V15M3,19H21V17H3V19M3,11H21V9H3V11M3,5V7H21V5H3Z"/>
        </svg>
      </div>
    `
      : "";
    const itemsHtml = config.items
      .map(([label, sensor]) => {
        const entityId = `sensor.${this._prefix}${sensor}`;
        let state = this._getEntityState(sensor);
        if (sensor === "ji_shen_fang_wei") {
          state = state.replace(/(.{10})/g, "$1<br>");
        }
        const isYiJiDengDi = sensor === "yi_ji_deng_di";
        const isJinriJiShen = sensor === "jin_ri_ji_shen";
        let valueClass = "info-value";
        if (isYiJiDengDi) valueClass += " yi-ji-deng-di";
        if (isJinriJiShen) valueClass += " jin-ri-ji-shen";
        return `
          <div class="info-item">
            <span class="info-label">${label}：</span>
            <span class="${valueClass}" data-entity="${entityId}">${state}</span>
          </div>
        `;
      })
      .join("");
    return `
      <div class="info-col" ${
        !this._isLocked ? 'draggable="true"' : ""
      } data-module="${moduleId}">
        <div class="info-group ${config.className}">
          ${handleHtml}
          <div class="info-title">${config.title}</div>
          <div class="info-content">${itemsHtml}</div>
        </div>
      </div>
    `;
  }
  updateContent() {
    if (!this._hass || !this.content) return;
    const date = this._getEntityState("ri_qi");
    const weekday = this._getEntityState("xing_qi");
    const lunar = this._getEntityState("nong_li");
    const bazi = this._getEntityState("ba_zi");
    const jieri = this._getEntityState("jin_ri_jie_ri");
    const yi = this._getEntityState("yi");
    const ji = this._getEntityState("ji");
    const filteredLunar = lunar.replace(/^[^\s]+\s*/, "");
    if (date === "N/A" || weekday === "N/A" || lunar === "N/A") {
      this.content.innerHTML = `
        <div class="container">
          <div class="banner error">
            <h3>无法加载黄历数据</h3>
            <p>请检查传感器配置和前缀设置</p>
            <p>注意默认前缀: ${this._prefix}</p>
          </div>
        </div>
      `;
      return;
    }
    this.content.innerHTML = `
      <div class="container">
        <div class="banner">
          <div class="kalendar_top">
            <div class="kalendar_date">
              <div class="date-control">
                <button class="date-control-btn" data-action="previous_day">&lt;</button>
                <div class="kalendar_date_clickable">
                  <span class="date-number">${date.split("-")[2]}</span>
                </div>
                <button class="date-control-btn" data-action="next_day">&gt;</button>
              </div>
            </div>
            <h3><span class="kalendar_date_text">${date}</span> · ${weekday} · ${jieri}</h3>
            <h5>${filteredLunar}「 ${bazi} 」</h5>
          </div>

          <div class="yi-ji-section">
            <div class="yi-ji-item">
              <div class="yi-ji-header">宜</div>
              <div class="yi-ji-content" data-entity="sensor.${
                this._prefix
              }yi">${yi}</div>
            </div>
            <div class="yi-ji-item">
              <div class="yi-ji-header">忌</div>
              <div class="yi-ji-content" data-entity="sensor.${
                this._prefix
              }ji">${ji}</div>
            </div>
          </div>
          ${this.renderInfoGrid()}
        </div>
      </div>
    `;
    requestAnimationFrame(() => {
      if (!this._isLocked) {
        this._initDragAndDrop();
      }
    });
  }
  handleDrop(e) {
    if (this._isLocked) return;
    e.preventDefault();
    const dropTarget = e.target.closest(".info-col");
    if (!dropTarget || !draggedItem) return;
    const dropRow = dropTarget.closest(".info-row");
    if (!dropRow) return;
    const moduleId = draggedItem.getAttribute("data-module");
    const targetModuleId = dropTarget.getAttribute("data-module");
    if (moduleId && targetModuleId && moduleId !== targetModuleId) {
      const rect = dropTarget.getBoundingClientRect();
      const insertBefore = e.clientX - rect.left < rect.width / 2;
      if (insertBefore) {
        dropRow.insertBefore(draggedItem, dropTarget);
      } else {
        dropRow.insertBefore(draggedItem, dropTarget.nextSibling);
      }
      this._updateLayoutFromDOM();
    }
    this.shadowRoot.querySelectorAll(".info-col").forEach((col) => {
      col.style.borderLeft = "";
      col.style.borderRight = "";
    });
  }

  getStyles() {
    return `
      :host {
        display: block;
        --card-accent: #ef4444;
      }

      ha-card {
        background: var(--card-background-color);
        color: var(--primary-text-color);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, none);
        padding: 16px;
        transition: all .3s ease-out;
        letter-spacing: 0.03em;
        position: relative;
      }

      .banner {
        background: var(--card-background-color);
        border-radius: var(--ha-card-border-radius, 12px);
        padding: 12px;
        box-shadow: var(--ha-card-box-shadow, none);
      }

      .yi-ji-item {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
      }

      .yi-ji-item:hover {
        border-color: var(--accent-color);
        box-shadow: 0 2px 8px var(--ha-card-box-shadow);
      }

      .info-group {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        position: relative;
      }

      .info-group:hover {
        border-color: var(--accent-color);
        box-shadow: 0 2px 8px var(--ha-card-box-shadow);
      }

      .info-title {
        color: var(--primary-text-color);
        border-bottom: 1px dashed var(--divider-color);
      }


      .kalendar_date_text {
        cursor: pointer;
        transition: opacity 0.3s ease;
      }
      
      .kalendar_date_clickable:hover {
        opacity: 0.8;
      }

    .date-picker-dialog {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999;
      backdrop-filter: blur(2px);
    }

    .date-picker-content {
      background: var(--card-background-color);
      border-radius: 12px;
      padding: 24px;
      min-width: 300px;
      max-width: 90vw;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    .date-picker-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .date-picker-header h3 {
      margin: 0;
      color: var(--primary-text-color);
    }

    .close-picker-button {
      background: none;
      border: none;
      padding: 8px;
      cursor: pointer;
      color: var(--primary-text-color);
      opacity: 0.7;
      transition: opacity 0.3s ease;
      border-radius: 50%;
    }

    .close-picker-button:hover {
      opacity: 1;
      background: var(--secondary-background-color);
    }

    .date-picker-input {
      width: 100%;
      padding: 12px;
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      background: var(--card-background-color);
      color: var(--primary-text-color);
      font-size: 16px;
      margin-bottom: 20px;
      box-sizing: border-box;
    }

    .date-picker-input:focus {
      outline: none;
      border-color: var(--primary-color);
    }

    .date-picker-buttons {
      display: flex;
      justify-content: center;
    }

    .confirm-date-button {
      padding: 10px 40px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: opacity 0.3s ease;
      font-size: 14px;
      background: var(--primary-color);
      color: var(--primary-color-text, white);
    }

    .confirm-date-button:hover {
      opacity: 0.9;
    }

      @media screen and (max-width: 768px) {
        .date-picker-content {
          padding: 16px;
          width: 90vw;
        }

        .date-picker-input {
          padding: 10px;
          font-size: 14px;
        }

        .confirm-date-button,
        .today-date-button {
          padding: 8px 16px;
          font-size: 13px;
        }
      }

      .kalendar_top h3, 
      .kalendar_top h5,
      .yi-ji-header, 
      .yi-ji-content,
      .info-label, 
      .info-value,
      .date-control button,
      .error p {
        color: var(--primary-text-color);
      }

      .yi-ji-content,
      .info-content,
      .kalendar_top h5 {
        opacity: 0.8;
      }

      .date-number {
        font-size: 56px;
        color: var(--card-accent);
        font-weight: 700;
        line-height: 1;
        display: block;
        min-width: 80px;
        text-align: center;
        cursor: pointer;
        transition: opacity 0.3s ease;
        user-select: none;
      }

      .date-number:hover {
        opacity: 0.8;
      }

      .date-control button {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 28px;
        padding: 4px;
        transition: all 0.3s ease;
        opacity: 0.8;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
      }

      .date-control button:hover {
        opacity: 1;
        color: var(--card-accent);
      }

      .date-control {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 180px;
        margin: 20px auto 0;
      }

      .container {
        width: 100%;
        box-sizing: border-box;
      }

      .kalendar_top {
        height: 97px;
        padding: 0 8px;
        text-align: center;
        margin-bottom: 16px;
        position: relative;
      }

      .kalendar_date {
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
      }

      .kalendar_top h3 {
        font-size: 14px;
        margin: 8px 0 4px;
        font-weight: 600;
      }

      .kalendar_top h5 {
        font-size: 12px;
        margin: 4px 0;
        font-weight: normal;
      }

      .yi-ji-section {
        margin: 40px 0 14px;
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
      }

      .yi-ji-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 8px;
        border-radius: 8px;
      }

      .yi-ji-header {
        font-family: -apple-system, STSongti-TC-Bold, Arial, sans-serif;
        font-size: 13px;
        font-weight: 600;
        white-space: nowrap;
        margin-top: -0.75px;
      }

      .yi-ji-content {
        font-size: 13px;
        line-height: 1.6;
        word-break: break-word;
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1;
        min-width: 0;
        position: relative;
        max-height: calc(1.6em * 2);
        padding-right: 1.25em;
        cursor: pointer;
        transition: opacity 0.3s ease;
      }

      .yi-ji-content:hover {
        opacity: 1;
      }

      .info-row {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
      }

      .info-row:last-child {
        margin-bottom: 0;
      }

      .info-col {
        flex: 1;
        min-width: 0;
        margin: 0;
      }

      .info-group {
        padding: 8px 10px;
        border-radius: 12px;
        height: 100%;
        box-sizing: border-box;
        transition: all 0.3s ease;
      }

      .info-title {
        font-size: 13px;
        font-family: -apple-system, STSongti-TC-Bold, Arial, sans-serif;
        font-weight: 600;
        margin-bottom: 6px;
        padding-bottom: 3px;
      }

      .info-content {
        font-size: 12px;
        line-height: 1.5;
      }

      .info-item {
        margin-bottom: 4px;
        display: flex;
        align-items: baseline;
      }

      .info-item:last-child {
        margin-bottom: 0;
      }

      .info-label {
        font-weight: 600;
        margin-right: 4px;
        flex-shrink: 0;
        font-size: 12px;
      }

      .info-value {
        word-break: break-all;
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1;
        min-width: 0;
        line-height: 1.5;
        cursor: pointer;
        letter-spacing: 0.05em;
        transition: opacity 0.3s ease;
      }

      .info-value:hover {
        opacity: 1;
      }

      .info-group.fangwei .info-value {
        -webkit-line-clamp: 3;
      }

      .jin-ri-ji-shen {
        min-height: 3.2em !important;
        display: -webkit-box !important;
        -webkit-line-clamp: 2 !important;
        line-height: 1.6 !important;
      }

      .yi-ji-deng-di {
        min-height: 3.2em !important;
        display: -webkit-box !important;
        -webkit-line-clamp: 2 !important;
        line-height: 1.6 !important;
      }

      .error {
        text-align: center;
        padding: 20px;
        color: var(--error-color, #db4437);
      }

      .error p {
        margin: 8px 0;
        opacity: 0.7;
      }

      .settings-button {
        position: absolute;
        top: 20px;
        right: 20px;
        background: none;
        border: none;
        padding: 8px;
        cursor: pointer;
        color: var(--primary-text-color);
        opacity: 0;
        transition: opacity 0.3s ease;
        z-index: 1;
      }

      ha-card:hover .settings-button {
        opacity: 0.5;
      }

      .settings-button:hover {
        opacity: 1 !important;
      }


      .settings-button svg {
        width: 20px;
        height: 20px;
      }

      .info-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-bottom: 8px;
      }

      .info-row:last-child {
        margin-bottom: 0;
      }

      .info-col {
        position: relative;
        cursor: move;
      }

      .info-col.empty {
        cursor: default;
      }

      .handle {
        position: absolute;
        top: 8px;
        right: 8px;
        width: 16px;
        height: 16px;
        opacity: 0;
        cursor: grab;
        transition: opacity 0.3s ease;
        color: var(--primary-text-color);
      }

      .info-group:hover .handle {
        opacity: 0.5;
      }

      .handle:hover {
        opacity: 1 !important;
      }

      .handle:active {
        cursor: grabbing;
      }

      .handle svg {
        width: 100%;
        height: 100%;
      }

      .info-col.dragging {
        opacity: 0.5;
      }


      .handle {
        position: absolute;
        top: 8px;
        right: 8px;
        width: 16px;
        height: 16px;
        opacity: 0;
        cursor: grab;
        transition: opacity 0.3s ease;
        color: var(--primary-text-color);
      }

      .info-group:hover .handle {
        opacity: 0.5;
      }

      .handle:hover {
        opacity: 1 !important;
      }

      .handle:active {
        cursor: grabbing;
      }

      .handle svg {
        width: 100%;
        height: 100%;
      }

      .module-manager-dialog {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 999;
        backdrop-filter: blur(2px);
      }

      .module-manager-content {
        background: var(--card-background-color);
        border-radius: 12px;
        padding: 24px;
        min-width: 300px;
        max-width: 90vw;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
      }

      .module-row {
        display: flex;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid var(--divider-color);
      }

      .module-row:last-child {
        border-bottom: none;
      }

      .module-row input[type="checkbox"] {
        margin-right: 12px;
      }
      
      .module-row span {
        color: var(--primary-text-color);
        font-size: 14px;
      }

      .close-button,
      .reset-button {
        padding: 10px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: opacity 0.3s ease;
        font-size: 14px;
      }

      .close-button {
        background: var(--primary-color);
        color: var(--primary-color-text, white);
      }

      .reset-button {
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
      }

      .close-button:hover,
      .reset-button:hover {
        opacity: 0.9;
      }

      .info-col.drag-over::before {
        content: "";
        position: absolute;
        top: 0;
        bottom: 0;
        width: 3px;
        background: var(--primary-color);
      }

      .info-col.drag-over-left::before {
        left: -1px;
      }

      .info-col.drag-over-right::before {
        right: -1px;
      }
      .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
      }

      .lock-button {
        background: none;
        border: none;
        padding: 8px;
        cursor: pointer;
        color: var(--primary-text-color);
        opacity: 0.7;
        transition: opacity 0.3s ease;
        border-radius: 50%;
      }

      .lock-button:hover {
        opacity: 1;
        background: var(--secondary-background-color);
      }

      .module-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        margin-bottom: 8px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        transition: all 0.3s ease;
      }

      .module-row:hover {
        border-color: var(--primary-color);
        background: var(--secondary-background-color);
      }

      .module-left {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .module-right {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--primary-text-color);
        opacity: 0.5;
      }

      .drag-hint {
        font-size: 12px;
      }

      .drag-icon {
        display: flex;
        align-items: center;
      }

      .buttons-container {
        display: flex;
        gap: 8px;
        margin-top: 20px;
      }

      .reset-button,
      .close-button {
        flex: 1;
        padding: 10px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 14px;
      }

      .reset-button {
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
      }

      .close-button {
        background: var(--primary-color);
        color: var(--primary-color-text, white);
      }

      .reset-button:hover,
      .close-button:hover {
        opacity: 0.9;
      } 
      @media screen and (max-width: 768px) {
        ha-card {
          padding: 4px !important;
        }

        .banner {
          padding: 8px;
        }

        .date-control {
          width: 160px;
        }

        .date-control button {
          font-size: 24px;
        }

        .yi-ji-section {
          display: grid;
          gap: 14px;  
        }

        .yi-ji-item {
          padding: 6px; 
        }

        .yi-ji-header {
          font-size: 12px;  
        }

        .yi-ji-content {
          font-size: 12px;
          padding-right: 1em;
        }

        .info-group {
          padding: 6px 8px;
        }

        .info-title {
          font-size: 12px;
        }

        .info-content {
          font-size: 11px;
        }
        
        .info-label,
        .info-value {
          font-size: 11px;
        }

        .settings-button {
          top: 8px;
          right: 8px;
          padding: 4px;
        }

        .settings-button svg {
          width: 16px;
          height: 16px;
        }

        .handle {
          top: 6px;
          right: 6px;
          width: 14px;
          height: 14px;
        }
      }
    `;
  }
}

customElements.define("almanac-card", AlmanacCard);
