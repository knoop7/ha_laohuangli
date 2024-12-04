class AlmanacCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._handleClick = this._handleClick.bind(this);
    this._handleDateControl = this._handleDateControl.bind(this);
    this._isLocked = true;
    this._showYiJi = true;
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
          ["卦象", "liu_shi_si_gua"],
          ["吉凶", "shi_chen_xiong_ji"],
        ],
      },
      shengxiao: {
        id: "shengxiao",
        enabled: true,
        className: "shengxiao",
        title: "孔明禽相",
        items: [
          ["六曜", "liu_yao"],
          ["三合", "jin_ri_san_he"],
          ["六合", "jin_ri_liu_he"],
          ["演禽", "san_shi_liu_qin"],
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
    if (!window.clicky) {
      (function () {
        var c = document.createElement("script");
        c.type = "text/javascript";
        c.async = 1;
        c.src = "//static.getclicky.com/js";
        var s = document.getElementsByTagName("script")[0];
        s.parentNode.insertBefore(c, s);
      })();
      window.clicky_site_ids = window.clicky_site_ids || [];
      window.clicky_site_ids.push(101470743);
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

      const savedYiJiState = localStorage.getItem("almanac-card-yiji");
      this._showYiJi = savedYiJiState ? JSON.parse(savedYiJiState) : true;
    } catch (e) {
      console.error("Error loading almanac card settings:", e);
      this._layout = this._defaultLayout;
      this._isLocked = true;
      this._showYiJi = true;
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
      localStorage.setItem("almanac-card-yiji", JSON.stringify(this._showYiJi));
    } catch (e) {
      console.error("Error saving almanac card settings:", e);
    }
  }

  toggleYiJi() {
    this._showYiJi = !this._showYiJi;
    this._saveSettings();
    this.updateContent();
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
    if (!this.card) {
      this.initialRender();
    }
    this.updateContent();
    this._showEffects();
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
    card.addEventListener("click", (e) => {
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
      '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97 0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65c-.04-.24-.25-.42-.5-.42h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49 1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1 0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66z"/></svg>';
    settingsButton.addEventListener("click", () => this._showModuleManager());

    card.appendChild(settingsButton);

    const style = document.createElement("style");
    style.textContent = this.getStyles();
    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this.card = card;

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

    const yiJiRow = document.createElement("div");
    yiJiRow.className = "module-row";
    const yiJiLeft = document.createElement("div");
    yiJiLeft.className = "module-left";
    const yiJiCheckbox = document.createElement("input");
    yiJiCheckbox.type = "checkbox";
    yiJiCheckbox.checked = this._showYiJi;
    yiJiCheckbox.addEventListener("change", () => {
      this.toggleYiJi();
    });
    const yiJiLabel = document.createElement("span");
    yiJiLabel.textContent = "显示宜忌";
    yiJiLeft.appendChild(yiJiCheckbox);
    yiJiLeft.appendChild(yiJiLabel);
    yiJiRow.appendChild(yiJiLeft);

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
      moduleList.insertBefore(yiJiRow, moduleList.firstChild);
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
      this._draggedItem = null;
      draggedItem = null;
      draggedParent = null;
    };
    this.shadowRoot.querySelectorAll(".info-col").forEach((col) => {
      if (!col.classList.contains("empty")) {
        col.setAttribute("draggable", "true");
        col.addEventListener("dragstart", handleDragStart);
        col.addEventListener("dragenter", handleDragEnter);
        col.addEventListener("dragover", handleDragOver);
        col.addEventListener("dragleave", handleDragLeave);
        col.addEventListener("drop", handleDrop);
        col.addEventListener("dragend", handleDragEnd);
      }
    });
  }
  _updateLayoutFromDOM() {
    const newLayout = [];
    this.shadowRoot.querySelectorAll(".info-row").forEach((row) => {
      const modules = Array.from(row.querySelectorAll(".info-col"))
        .filter((col) => !col.classList.contains("empty"))
        .map((col) => col.getAttribute("data-module"))
        .filter(Boolean);

      if (modules.length > 0) {
        while (modules.length < 2) {
          modules.push(null);
        }
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
      this._layout.forEach((row) => {
        const validRow = row.filter((id) => id && enabledModules.includes(id));
        if (validRow.length > 0) {
          while (validRow.length < 2) validRow.push(null);
          layout.push(validRow);
        }
      });
    }

    const usedModules = new Set(layout.flat().filter(Boolean));
    const remainingModules = enabledModules.filter(
      (id) => !usedModules.has(id)
    );

    for (let i = 0; i < remainingModules.length; i += 2) {
      layout.push([
        remainingModules[i],
        i + 1 < remainingModules.length ? remainingModules[i + 1] : null,
      ]);
    }

    return layout
      .map(
        (row, rowIndex) =>
          `<div class="info-row" data-row="${rowIndex}">
                ${
                  row[0]
                    ? this.renderInfoCol(row[0])
                    : `<div class="info-col empty" ${
                        !this._isLocked ? 'draggable="true"' : ""
                      }></div>`
                }
                ${
                  row[1]
                    ? this.renderInfoCol(row[1])
                    : `<div class="info-col empty" ${
                        !this._isLocked ? 'draggable="true"' : ""
                      }></div>`
                }
              </div>`
      )
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

  _limitWords(text, limit = 10) {
    const words = text.trim().split(/\s+/);
    return words.slice(0, limit).join(" ");
  }

  updateContent() {
    if (!this._hass || !this.card) return;

    const date = this._getEntityState("ri_qi");
    const weekday = this._getEntityState("xing_qi");
    const lunar = this._getEntityState("nong_li");
    const bazi = this._getEntityState("ba_zi");
    const jieri = this._getEntityState("jin_ri_jie_ri")
      .split("（")
      .map((item) => {
        const text = item.replace(/）.*$/, "").trim();
        return text
          ? `<span class="festival-text ${
              text.length === 2 ? "festival-two-char" : ""
            }">${text}</span>`
          : "";
      })
      .filter((item) => item);
    const yi = this._getEntityState("yi")
      .split(/[，。]/)[0]
      .split(" ")
      .slice(0, 7)
      .join(" ");
    const ji = this._getEntityState("ji")
      .split(/[，。]/)[0]
      .split(" ")
      .slice(0, 7)
      .join(" ");

    const filteredLunar = lunar.replace(/^[^\s]+\s*/, "");

    const festivalsHtml = jieri.length
      ? `
      <div class="festival-carousel">
        ${jieri
          .map((festival, index) => {
            const needsScroll = festival.length > 10;
            return `
          <div class="festival-item" style="display: ${
            index === 0 ? "block" : "none"
          }">
            <div class="festival-card">
              <div class="festival-content${
                needsScroll ? " scroll-text" : ""
              }">${festival}</div>
            </div>
          </div>
        `;
          })
          .join("")}
      </div>
    `
      : "";

    if (date === "N/A" || weekday === "N/A" || lunar === "N/A") {
      this.card.innerHTML = `
            <div class="banner error">
              <h3>无法加载黄历数据</h3>
              <p>请检查传感器配置和前缀设置</p>
              <p>注意默认前缀: ${this._prefix}</p>
            </div>
          `;
      return;
    }

    const yiJiSection = this._showYiJi
      ? `
        <div class="yi-ji-section">
          <div class="yi-ji-item">
            <div class="yi-ji-header">宜</div>
            <div class="yi-ji-content" data-entity="sensor.${this._prefix}yi">${yi}</div>
          </div>
          <div class="yi-ji-item">
            <div class="yi-ji-header">忌</div>
            <div class="yi-ji-content" data-entity="sensor.${this._prefix}ji">${ji}</div>
          </div>
        </div>
      `
      : "";

    this.card.innerHTML = `
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
              <h3><span class="kalendar_date_text">${date}</span> · ${weekday} ·${festivalsHtml}</h3>
              <h5>${filteredLunar}「 ${bazi} 」</h5>
            </div>
    
            ${yiJiSection}
            ${this.renderInfoGrid()}
          </div>
        `;

    const settingsButton = document.createElement("button");
    settingsButton.className = "settings-button";
    settingsButton.innerHTML =
      '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97 0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65c-.04-.24-.25-.42-.5-.42h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49 1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1 0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66z"/></svg>';
    settingsButton.addEventListener("click", () => this._showModuleManager());
    this.card.appendChild(settingsButton);

    if (jieri.length > 1) {
      this._initFestivalCarousel();
    }

    requestAnimationFrame(() => {
      if (!this._isLocked) {
        this._initDragAndDrop();
      }
      const dateElements = this.shadowRoot.querySelectorAll(
        ".kalendar_date_text, .date-number"
      );
      dateElements.forEach((element) => {
        element.removeEventListener("click", this._handleClick);
        element.addEventListener("click", this._handleClick);
      });
    });
  }

  _initFestivalCarousel() {
    const carousel = this.shadowRoot.querySelector(".festival-carousel");
    if (!carousel) return;

    const items = Array.from(carousel.querySelectorAll(".festival-item"));
    if (items.length <= 1) return;

    let currentIdx = 0;
    setInterval(() => {
      items[currentIdx].style.display = "none";
      currentIdx = (currentIdx + 1) % items.length;
      items[currentIdx].style.display = "block";

      const card = items[currentIdx].querySelector(".festival-card");
      card.classList.add("flip-in");
      setTimeout(() => card.classList.remove("flip-in"), 800);
    }, 3000);
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
    --transition-bezier: cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  ha-card {
    background: var(--card-background-color);
    color: var(--primary-text-color);
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: var(--ha-card-box-shadow, none);
    padding: 20px;
    transition: all .3s ease-out;
    letter-spacing: 0.1em;
    position: relative;
    overflow: visible; 
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
  
  .settings-button svg {
    width: 20px;
    height: 20px;
    display: block;
  }
  
  ha-card:hover .settings-button {
    opacity: 0.5;
  }
  
  .settings-button:hover {
    opacity: 1 !important;
  }
  
  .banner {
    background: var(--card-background-color);
    border-radius: var(--ha-card-border-radius, 12px);
    padding: 16px;
    box-shadow: var(--ha-card-box-shadow, none);
  }
  
.kalendar_top {
  height: 97px;
  padding: 0 8px;
  text-align: center;
  margin-bottom: 20px;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
}

.kalendar_date {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-top: -18px;
  flex: 0 0 auto;
}

  .date-header {
    white-space: nowrap;
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    position: relative;
    flex: 0 0 auto;
  }

  .date-header > * {
    margin: 0;
  }

  .kalendar_top h3 {
      font-size: 15px;
      margin-top: 0px;
      margin-bottom: 10px;
      font-weight: 600;
      color: var(--primary-text-color);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      width: 100%;
      text-align: center;
      letter-spacing: 2px; 
  }
  .kalendar_top h3 span.text {
      letter-spacing: 33px; 
  }
  .kalendar_top h3 span.number {
      letter-spacing: 0;
  }


  .kalendar_top h5 {
    font-size: 12px;
    margin: -8px 0;
    font-weight: normal;
    color: var(--primary-text-color);
    opacity: 0.7;
    flex: 0 0 auto;
    width: 100%;
    text-align: center;
  }
  .kalendar_date_text {
    cursor: pointer;
    transition: opacity 0.3s ease;
  }
  
  .kalendar_date_clickable:hover {
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
  
  .date-control {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 180px;
    margin: 20px auto 0;
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
    color: var(--primary-text-color);
  }
  
  .date-control button:hover {
    opacity: 1;
    color: var(--card-accent);
  }
  
    .yi-ji-section {
    margin: 0 0 10px;
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    }

    .yi-ji-section ~ .info-row:first-of-type {
      margin-top: 20px;
    }
  
  .yi-ji-item {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 9px;
  }
  
  .yi-ji-item:hover {
    border-color: var(--accent-color);
    box-shadow: 0 2px 8px var(--ha-card-box-shadow);
  }
  
  .yi-ji-header {
    font-family: -apple-system, STSongti-TC-Bold, Arial, sans-serif;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    margin-top: -0.75px;
    color: var(--primary-text-color);
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
    color: var(--primary-text-color);
    opacity: 0.8;
  }
  
  .yi-ji-content:hover {
    opacity: 1;
  }
  
  .info-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-bottom: 6px;
  }
  
  .info-row:last-child {
    margin-bottom: 0;
  }
  
  .info-col {
    position: relative;
    min-width: 0;
    margin: 0;
    cursor: default;  
  }
  
  .info-col[draggable="true"]:not(.empty) {
    cursor: grab;
  }
  
  .info-col.empty {
    cursor: default;
  }
  
  .info-col.dragging {
    opacity: 0.5;
    cursor: grabbing;
  }
  
  .info-col[draggable="true"]:not(.empty):active {
    cursor: grabbing;
  }
  
  .info-group {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    position: relative;
    padding: 18px 20px;
    border-radius: 12px;
    height: 100%;
    box-sizing: border-box;
    transition: all 0.3s ease;
    box-shadow: 0 0 0 rgba(0,0,0,0);
  }
  
  .info-group:hover {
    border-color: var(--accent-color);
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    transform: translateY(-1px);
  }
  
  .info-title {
    color: var(--primary-text-color);
    border-bottom: 1px dashed var(--divider-color);
    font-size: 13px;
    font-family: -apple-system, STSongti-TC-Bold, Arial, sans-serif;
    font-weight: 600;
    margin-bottom: 4px;
    padding-bottom: 4px;
  }
  
  .info-content {
    font-size: 12px;
    line-height: 1.5;
    opacity: 0.8;
  }
  
  .info-item {
    margin-bottom: 4px;
    display: flex;
    align-items: baseline;
    position: relative;
    transition: all 0.3s var(--transition-bezier);
    justify-content: space-between;
    gap: 8px;
  }
  
  .info-item:last-child {
    margin-bottom: 0;
  }
  
  .info-label {
    color: var(--primary-text-color);
    opacity: 0.7;
    font-weight: 450;
    font-size: 12px;
    flex-shrink: 0;
    letter-spacing: 0.13em;
  }
  
  .info-value {
    word-break: break-all;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
    min-width: 40%;
    text-align: right;
    padding: 2px 0px 1px 0px; 
    border-radius: 4px;
    position: relative;
    margin-bottom: -5px;
  
    margin-left: -8px;         
    z-index: 1;
    color: var(--primary-text-color);
    font-size: 12px;
    line-height: 1.4;
    letter-spacing: 0.1em;
    word-spacing: 1px;
    cursor: pointer;
  }
  
    
  .info-value:active {
    transform: translateX(-1px) scale(0.99);
  }
  
  
  .info-value:hover::before {
    height: 70%;
    opacity: 0.6;
  }
  
  .info-value::after {
    content: '';
    position: absolute;
    top: 50%;
    right: 0;
    width: 2px;
    height: 2px;
    background: var(--primary-color);
    opacity: 0;
    border-radius: 50%;
    transition: all 0.6s var(--transition-bezier);
    transform: translate(0, -50%) scale(1);
    z-index: -1;
  }
  
  .info-value:active::after {
    opacity: 0.1;
    width: 100%;
    height: 100%;
    transform: translate(0, -50%) scale(1);
    border-radius: 4px;
  }
  
  .info-value[data-length="long"] {
    -webkit-line-clamp: 3;
    font-size: 11px;
    line-height: 1.5;
  }
  
  .info-value[data-importance="high"] {
    color: var(--error-color, #ef4444);
    font-weight: 600;
  }
  
  .info-value[data-importance="warning"] {
    color: var(--warning-color, #f59e0b);
  }
  
  .info-value[data-importance="success"] {
    color: var(--success-color, #10b981);
  }
  
  .info-value[data-type="date"] {
    font-family: var(--font-family-mono, monospace);
    letter-spacing: 0.1em;
  }
  
  .info-value[data-type="number"] {
    font-variant-numeric: tabular-nums;
  }
  
  .info-value:hover::after {
    opacity: 1;
    transform: translateY(0);
  }
  .info-value.jin-ri-ji-shen {
    margin-left: -5px;
  }

  .festival-carousel {
    display: inline-block;
    vertical-align: middle;
  }

  .festival-item {
    display: none;
  }

  .festival-card {
    position: relative;
    min-width: 60px;
  }

  .festival-content {
    padding: 0 4px;
    margin-bottom: 0.5px;
  }

  .festival-two-char {
    margin-left: -1.5em; 
  }
    
  .festival-text {
    display: inline-block;
  }

  .festival-card.flip-in {
    animation: flipIn 12s ease-out infinite; 
  }

  @keyframes flipIn {
    0% {
      opacity: 0;
      transform: rotateX(180deg);
    }
    8.33% {
      opacity: 1;
      transform: rotateX(0deg);
    }
    91.67% {
      opacity: 1;
      transform: rotateX(0deg); 
    }
    100% {
      opacity: 0;
      transform: rotateX(180deg);
    }
  }


  @media (prefers-color-scheme: dark) {
    .info-value {
      background: linear-gradient(
        to right,
        transparent,
        rgba(255, 255, 255, 0.03)
      );
    }
    
    .info-value:hover {
      background: linear-gradient(
        to right,
        transparent,
        rgba(255, 255, 255, 0.08)
      );
    }
  }
 


  
  .jin-ri-ji-shen,
  .yi-ji-deng-di {
    display: -webkit-box !important;
    -webkit-line-clamp: 1 !important;
    line-height: 1.6 !important;
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
  
  .handle svg {
    width: 100%;
    height: 100%;
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
  
  .module-manager-dialog,
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
    z-index: 9999;
    backdrop-filter: blur(2px);
  }
  
  .module-manager-content,
  .date-picker-content {
    background: var(--card-background-color, #fff);
    border-radius: 12px;
    padding: 24px;
    min-width: 300px;
    max-width: 90vw;
    position: relative;
    box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.1));
    animation: dialogSlideIn 0.3s ease-out;
  }
  
  .module-manager-content {
    max-height: 90vh;
    overflow-y: auto;
  }
  

  @keyframes dialogSlideIn {
    from {
      opacity: 0;
      transform: translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .date-picker-header,
  .header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--divider-color);
    padding-bottom: 12px;
  }
  
  .date-picker-header h3,
  .header-container h3 {
    margin: 0;
    color: var(--primary-text-color);
    font-size: 16px;
    font-weight: 500;
  }
  
  .close-picker-button,
  .lock-button {
    background: none;
    border: none;
    padding: 8px;
    cursor: pointer;
    color: var(--primary-text-color);
    opacity: 0.7;
    transition: all 0.2s ease;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
  }
  
  .close-picker-button:hover,
  .lock-button:hover {
    opacity: 1;
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
  }
  
  .date-picker-input {
    width: 100%;
    padding: 12px;
    border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    border-radius: 8px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color);
    font-size: 16px;
    margin-bottom: 20px;
    box-sizing: border-box;
    transition: all 0.2s ease;
  }
  
  .date-picker-input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(var(--rgb-primary-color), 0.2);
  }
  
  .date-picker-buttons,
  .buttons-container {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
  }
  
  .confirm-date-button,
  .reset-button,
  .close-button {
    padding: 8px 24px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
    min-width: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .confirm-date-button,
  .close-button {
    background: var(--primary-color);
    color: var(--primary-color-text, white);
  }
  
  .reset-button {
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
    color: var(--primary-text-color);
  }
  
  .confirm-date-button:hover,
  .close-button:hover,
  .reset-button:hover {
    opacity: 0.9;
    transform: translateY(-1px);
  }
  
  .module-list {
    margin: 0 -8px;
    padding: 0 8px;
    max-height: 60vh;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--primary-color) transparent;
  }
  
  .module-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    margin-bottom: 8px;
    border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    border-radius: 8px;
    transition: all 0.2s ease;
  }
  
  .module-row:hover {
    border-color: var(--primary-color);
    background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
    transform: translateX(2px);
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
    color: var(--secondary-text-color);
  }
  
  .drag-hint {
    font-size: 12px;
    opacity: 0.7;
  }
  
  .drag-icon {
    opacity: 0.5;
    transition: opacity 0.2s ease;
  }
  
  .module-row:hover .drag-icon {
    opacity: 1;
  }
  
  .module-list::-webkit-scrollbar {
    width: 6px;
  }
  
  .module-list::-webkit-scrollbar-track {
    background: transparent;
  }
  
  .module-list::-webkit-scrollbar-thumb {
    background-color: var(--primary-color);
    border-radius: 3px;
    border: 2px solid transparent;
  }
  
  .module-row input[type="checkbox"] {
    width: 18px;
    height: 18px;
    margin: 0;
    cursor: pointer;
    position: relative;
    border: 2px solid var(--primary-color);
    border-radius: 4px;
    background: transparent;
    transition: all 0.2s ease;
    appearance: none;
    -webkit-appearance: none;
  }
  
  .module-row input[type="checkbox"]:checked {
    background-color: var(--primary-color);
  }
  
  .module-row input[type="checkbox"]:checked::after {
    content: "";
    position: absolute;
    left: 5px;
    top: 2px;
    width: 4px;
    height: 8px;
    border: solid white;
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }
  
  @media screen and (max-width: 768px) {
    .kalendar_top {
      height: 80px;
    }
  
    .date-number {
      font-size: 44px;
      min-width: 65px;
    }
  
    .date-control {
      width: 150px;
      margin: 12px auto 0;
    }
  
    .yi-ji-section {
      margin: 35px 0 10px;   
      gap: 6px;             
    }
  
     .info-value {
      font-size: 10px;
      padding: 2px 0px 1px 0px;  
      margin-left: -15px;        
      overflow: hidden;          
      margin-bottom: -7px;
  
    }
  
    .info-value[data-length="long"] {
      font-size: 10px;
    }
    
    .module-manager-content,
    .date-picker-content {
      padding: 16px;
      width: calc(100vw - 32px);
      margin: 16px;
      max-height: calc(100vh - 32px);
    }
    
    .confirm-date-button,
    .reset-button,
    .close-button {
      padding: 8px 16px;
      font-size: 13px;
    }
    
    .date-picker-input {
      font-size: 14px;
      padding: 10px;
    }
  
  } 
  
  .festive-effects {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1000;
  }

.pyro {
 position: absolute;
 width: 100%;
 height: 100%;
 z-index: 10;
}

.pyro > .before, .pyro > .after {
 position: absolute;
 width: 5px;
 height: 5px;
 border-radius: 50%;
 box-shadow: 0 0 #fff;
 animation: 8s bang cubic-bezier(0.4, 0, 0.2, 1) infinite,
            8s gravity cubic-bezier(0.4, 0, 0.2, 1) infinite,
            16s position cubic-bezier(0.25, 0.1, 0.25, 1) infinite;
 opacity: 0.9;
}

.pyro > .after {
 animation-delay: 4s;
}

@keyframes bang {
 0% { box-shadow: 0 0 #fff; }
 30%, 50% {
   box-shadow: 
     -100px -100px #ff3333,
     160px -160px #ffdd33,
     -50px -50px #33ff33,
     130px -80px #3333ff,
     -100px -60px #ff33ff,
     50px -130px #33ffff,
     -80px -40px #ff8833,
     100px -100px #88ff33,
     -130px -30px #3388ff,
     30px -160px #ff3388;
 }
 100% { box-shadow: 0 0 #fff; opacity: 0; }
}

@keyframes gravity {
 0% { transform: translateY(0); }
 50% { transform: translateY(120px); }
 100% { transform: translateY(200px); }
}

@keyframes position {
 0%, 30% { margin-top: 10%; margin-left: 40%; }
 35%, 60% { margin-top: 15%; margin-left: 50%; }
 65%, 90% { margin-top: 20%; margin-left: 60%; }
 95%, 100% { margin-top: 10%; margin-left: 40%; }
}
  .deng-box {
    position: absolute;
    top: -10px;
    left: 0px;
    z-index: 999;  
    transform: scale(0.4);
    transform-origin: top left;
  }

  .deng-box.right {
    left: auto;
    right: 0px;
    transform-origin: top right;
  }

  .deng {
    position: relative;
    width: 120px;
    height: 90px;
    margin: 50px;
    background: rgba(216, 0, 15, 0.8);
    border-radius: 50% 50%;
    transform-origin: 50% -100px;
    animation: swing 3s infinite ease-in-out;
    box-shadow: -5px 5px 50px 4px rgba(250, 108, 0, 0.8);
  }

  .deng-a {
    width: 100px;
    height: 90px;
    background: rgba(216, 0, 15, 0.1);
    margin: 12px 8px 8px 8px;
    border-radius: 50% 50%;
    border: 2px solid #dc8f03;
  }

  .deng-b {
    width: 45px;
    height: 90px;
    background: rgba(216, 0, 15, 0.1);
    margin: -4px 8px 8px 26px;
    border-radius: 50% 50%;
    border: 2px solid #dc8f03;
  }

  .xian {
    position: absolute;
    top: -20px;
    left: 60px;
    width: 2px;
    height: 20px;
    background: #dc8f03;
  }

  .shui-a {
    position: relative;
    width: 5px;
    height: 20px;
    margin: -5px 0 0 59px;
    animation: swing 4s infinite ease-in-out;
    transform-origin: 50% -45px;
    background: #ffa500;
    border-radius: 0 0 5px 5px;
  }

  .shui-b {
    position: absolute;
    top: 14px;
    left: -2px;
    width: 10px;
    height: 10px;
    background: #dc8f03;
    border-radius: 50%;
  }

  .shui-c {
    position: absolute;
    top: 18px;
    left: -2px;
    width: 10px;
    height: 35px;
    background: #ffa500;
    border-radius: 0 0 0 5px;
  }

  .deng:before {
    position: absolute;
    top: -7px;
    left: 29px;
    height: 12px;
    width: 60px;
    content: " ";
    display: block;
    z-index: 999;
    border-radius: 5px 5px 0 0;
    border: solid 1px #dc8f03;
    background: linear-gradient(to right, #dc8f03, #ffa500, #dc8f03, #ffa500, #dc8f03);
  }

  .deng:after {
    position: absolute;
    bottom: -7px;
    left: 10px;
    height: 12px;
    width: 60px;
    content: " ";
    display: block;
    margin-left: 20px;
    border-radius: 0 0 5px 5px;
    border: solid 1px #dc8f03;
    background: linear-gradient(to right, #dc8f03, #ffa500, #dc8f03, #ffa500, #dc8f03);
  }

  .deng-t {
    font-family: 华文行楷, Arial, Lucida Grande, Tahoma, sans-serif;
    font-size: 3.2rem;
    color: #dc8f03;
    font-weight: bold;
    line-height: 85px;
    text-align: center;
  }

  @keyframes swing {
    0% { transform: rotate(-10deg) }
    50% { transform: rotate(10deg) }
    100% { transform: rotate(-10deg) }
  }
`;
  }

  _showEffects() {
    const card = this.shadowRoot.querySelector("ha-card");
    if (!card || !this._hass) return;

    const existingEffects = card.querySelector(".festive-effects");
    if (existingEffects) existingEffects.remove();

    const dateValue = this._getEntityState("ri_qi");
    if (dateValue === "N/A") return;

    const effects = document.createElement("div");
    effects.className = "festive-effects";

    const newYearDate = "2025-01-01";
    const springFestivalDates = new Set([
      "2025-01-28",
      "2025-01-29",
      "2025-01-30",
      "2025-01-31",
      "2025-02-01",
      "2025-02-02",
      "2025-02-03",
      "2025-02-04",
    ]);

    if (dateValue === newYearDate) {
      effects.innerHTML = `
        <div class="pyro">
          <div class="before"></div>
          <div class="after"></div>
        </div>
      `;
    } else if (springFestivalDates.has(dateValue)) {
      effects.innerHTML = `
        <div class="deng-box">
          <div class="deng">
            <div class="xian"></div>
            <div class="deng-a">
              <div class="deng-b"><div class="deng-t"></div></div>
            </div>
            <div class="shui shui-a"><div class="shui-c"></div><div class="shui-b"></div></div>
          </div>
        </div>
        <div class="deng-box right">
          <div class="deng">
            <div class="xian"></div>
            <div class="deng-a">
              <div class="deng-b"><div class="deng-t"></div></div>
            </div>
            <div class="shui shui-a"><div class="shui-c"></div><div class="shui-b"></div></div>
          </div>
        </div>
      `;
    }

    if (effects.innerHTML) {
      card.appendChild(effects);
    }
  }
}

customElements.define("almanac-card", AlmanacCard);
