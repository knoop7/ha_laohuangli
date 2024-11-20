class AlmanacCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._handleClick = this._handleClick.bind(this);
    this._handleDateControl = this._handleDateControl.bind(this);
    this._prefix = "zhong_guo_lao_huang_li_";
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
      } else if (e.target.classList.contains("date-number")) {
        this._handleDateControl("today");
      } else if (
        e.target.classList.contains("info-value") ||
        e.target.classList.contains("yi-ji-content")
      ) {
        this._handleClick(e);
      }
    });
    card.appendChild(content);
    this.content = content;

    const style = document.createElement("style");
    style.textContent = this.getStyles();
    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
  }

  _handleDateControl(action) {
    if (this._hass) {
      this._hass.callService("tgtg", "date_control", {
        action: action,
      });
    }
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
                <span class="date-number">${date.split("-")[2]}</span>
                <button class="date-control-btn" data-action="next_day">&gt;</button>
              </div>
            </div>
            <h3>${date} · ${weekday} · ${jieri}</h3>
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
  }

  renderInfoGrid() {
    return `
      <div class="info-row">
        ${this.renderInfoCol("jieqi", "节律太阴", [
          ["周数", "zhou_shu"],
          ["季节", "ji_jie"],
          ["节气", "jie_qi"],
          ["星座", "xing_zuo"],
          ["月相", "yue_xiang"],
        ])}
        ${this.renderInfoCol("other", "卜筮术数", [
          ["纳音", "na_yin"],
          ["星次", "xing_ci"],
          ["飞星", "jiu_gong_fei_xing"],
          ["廿八宿", "nian_ba_su"],
          ["十二神", "shi_er_shen"],
        ])}
      </div>
      <div class="info-row">
        ${this.renderInfoCol("shichen", "日时禄位", [
          ["日禄", "ri_lu"],
          ["时辰", "shi_chen"],
          ["经络", "shi_chen_jing_luo"],
          ["吉凶", "shi_chen_xiong_ji"],
        ])}
        ${this.renderInfoCol("shengxiao", "孔明生肖", [
          ["六曜", "liu_yao"],
          ["三合", "jin_ri_san_he"],
          ["六合", "jin_ri_liu_he"],
          ["冲煞", "sheng_xiao_chong_sha"],
        ])}
      </div>
      <div class="info-row">
        ${this.renderInfoCol("fangwei", "胎忌利向", [
          ["胎神", "jin_ri_tai_shen"],
          ["百忌", "peng_zu_bai_ji"],
          ["方位", "ji_shen_fang_wei"],
        ])}
        ${this.renderInfoCol("jixiong", "神煞吉凶", [
          ["吉神", "jin_ri_ji_shen"],
          ["凶煞", "jin_ri_xiong_sha"],
          ["等第", "yi_ji_deng_di"],
        ])}
      </div>
    `;
  }

  renderInfoCol(className, title, items) {
    const itemsHtml = items
      .map(([label, sensor]) => {
        const entityId = `sensor.${this._prefix}${sensor}`;
        let state = this._getEntityState(sensor);

        if (sensor === "ji_shen_fang_wei") {
          state = state.replace(/(.{10})/g, "$1<br>");
        }
        const isYiJiDengDi = sensor === "yi_ji_deng_di";
        const valueClass = isYiJiDengDi
          ? "info-value yi-ji-deng-di"
          : "info-value";

        return `
        <div class="info-item">
          <span class="info-label">${label}：</span>
          <span class="${valueClass}" data-entity="${entityId}">
            ${state}
          </span>
        </div>
      `;
      })
      .join("");

    return `
      <div class="info-col">
        <div class="info-group ${className}">
          <div class="info-title">${title}</div>
          <div class="info-content">${itemsHtml}</div>
        </div>
      </div>
    `;
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
      }

      .info-group:hover {
        border-color: var(--accent-color);
        box-shadow: 0 2px 8px var(--ha-card-box-shadow);
      }

      .info-title {
        color: var(--primary-text-color);
        border-bottom: 1px dashed var(--divider-color);
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
        -webkit-line-clamp: 2;
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

      @media screen and (max-width: 500px) {
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
      }
    `;
  }
}

customElements.define("almanac-card", AlmanacCard);
