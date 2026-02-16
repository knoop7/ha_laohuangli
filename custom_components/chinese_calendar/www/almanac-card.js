if (!window._lunarLoaded) {
  window._lunarLoaded = true;
  const s = document.createElement("script");
  s.src = "https://cdn.jsdelivr.net/npm/lunar-javascript@1.6.1/lunar.min.js";
  document.head.appendChild(s);
}
if (!window._notoSerifLoaded) {
  window._notoSerifLoaded = true;
  const lk = document.createElement("link");
  lk.rel = "stylesheet";
  lk.href = "https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&display=swap";
  document.head.appendChild(lk);
}
if (!window._fzFontLoaded) {
  window._fzFontLoaded = true;
  const st = document.createElement("style");
  st.textContent = '@font-face{font-family:"FZCuSong";src:url("https://psstatic.cdn.bcebos.com/video/FZCSJW_1679570337000.TTF") format("truetype");font-weight:normal;font-style:normal;font-display:swap}';
  document.head.appendChild(st);
}

function _getLunarDay(y, m, d) {
  try {
    if (typeof Solar === "undefined") return { text: "", special: false };
    const solar = Solar.fromYmd(y, m, d);
    const lunar = solar.getLunar();
    const jq = lunar.getJieQi();
    if (jq) return { text: jq, special: true };
    const sf = solar.getFestivals();
    if (sf && sf.length > 0) return { text: sf[0].length > 4 ? sf[0].slice(0, 4) : sf[0], special: true };
    const lf = lunar.getFestivals();
    if (lf && lf.length > 0) return { text: lf[0].length > 4 ? lf[0].slice(0, 4) : lf[0], special: true };
    const day = lunar.getDayInChinese();
    if (day === "初一") return { text: lunar.getMonthInChinese() + "月", special: false };
    return { text: day, special: false };
  } catch(e) {}
  return { text: "", special: false };
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "almanac-card",
  name: "中国老黄历",
  description: "One-stop | Traditional Chinese calendar information, feel the charm of traditional culture in a modern smart home system.",
  preview: true,
  documentationURL: "https://github.com/knoop7/ha_laohuangli"
});

class AlmanacCard extends HTMLElement {
  static getConfigElement() { return document.createElement("almanac-card-editor"); }
  static getStubConfig() {
    return { prefix: "zhong_guo_lao_huang_li_", show_yiji: true, show_festivals: true, grid_options: { columns: 12, rows: 6 } };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._prefix = "zhong_guo_lao_huang_li_";
    this._detailOpen = false;
    this._viewDate = new Date();
  }

  setConfig(config) {
    this._prefix = config.prefix || "zhong_guo_lao_huang_li_";
    this.config = { ...config, show_yiji: config.show_yiji !== false, show_festivals: config.show_festivals !== false, grid_options: config.grid_options ?? { columns: 12, rows: 6 } };
  }

  getCardSize() { return 6; }

  _s(sensor) {
    const id = `sensor.${this._prefix}${sensor}`;
    return this._hass?.states[id]?.state || "N/A";
  }

  _sa(sensor) {
    const id = `sensor.${this._prefix}${sensor}`;
    return this._hass?.states[id]?.attributes || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._update();
  }

  _build() {
    this._built = true;
    this._style = document.createElement("style");
    this._style.textContent = this._css();
    this.shadowRoot.appendChild(this._style);
    const c = document.createElement("ha-card");
    this.shadowRoot.appendChild(c);
    this._card = c;

    this._lpTimer = null;
    this._lpFired = false;
    const _getCell = (e) => (e.target || e.srcElement).closest(".day-cell[data-day]");
    const _selectDate = (cell) => {
      const d = parseInt(cell.dataset.day);
      const y = cell.dataset.year ? parseInt(cell.dataset.year) : this._viewDate.getFullYear();
      const m = cell.dataset.month ? parseInt(cell.dataset.month) - 1 : this._viewDate.getMonth();
      const dateStr = `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
      if (this._hass) this._hass.callService("chinese_calendar", "date_control", { action: "select_date", date: dateStr });
      return dateStr;
    };
    c.addEventListener("pointerdown", (e) => {
      const cell = _getCell(e);
      if (!cell) return;
      this._lpFired = false;
      this._lpTimer = setTimeout(() => {
        this._lpFired = true;
        _selectDate(cell);
        setTimeout(() => { this._detailOpen = true; this._update(); }, 300);
      }, 500);
    });
    const cancelLp = () => { if (this._lpTimer) { clearTimeout(this._lpTimer); this._lpTimer = null; } };
    c.addEventListener("pointerup", cancelLp);
    c.addEventListener("pointercancel", cancelLp);
    c.addEventListener("pointermove", (e) => { if (Math.abs(e.movementX) > 5 || Math.abs(e.movementY) > 5) cancelLp(); });
    c.addEventListener("click", (e) => {
      if (e.target.closest(".month-prev")) { const y = this._viewDate.getFullYear(), m = this._viewDate.getMonth(); this._viewDate = new Date(y, m - 1, 1); this._update(); return; }
      if (e.target.closest(".month-next")) { const y = this._viewDate.getFullYear(), m = this._viewDate.getMonth(); this._viewDate = new Date(y, m + 1, 1); this._update(); return; }
      if (this._lpFired) return;
      const cell = _getCell(e);
      if (cell) { _selectDate(cell); this._update(); }
    });
  }

  _closeDetail() {
    this._detailOpen = false;
    if (this._overlayEl) { this._overlayEl.remove(); this._overlayEl = null; }
    this._update();
  }

  _showDetailOverlay(data) {
    if (this._overlayEl) this._overlayEl.remove();
    const wrap = document.createElement("div");
    wrap.innerHTML = `<style>${this._css()}</style>${this._renderDetail(data)}`;
    wrap.style.cssText = "position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;padding:0";
    const bg = document.createElement("div");
    bg.style.cssText = "position:absolute;inset:0;background:rgba(28,25,23,0.4);backdrop-filter:blur(2px);animation:dp-fade .4s ease-out";
    bg.addEventListener("click", () => this._closeDetail());
    wrap.prepend(bg);
    wrap.querySelector(".dp-close")?.addEventListener("click", () => this._closeDetail());
    document.body.appendChild(wrap);
    this._overlayEl = wrap;
  }

  _getMonthDays(year, month) {
    return new Date(year, month + 1, 0).getDate();
  }

  _getFirstDayOfWeek(year, month) {
    const d = new Date(year, month, 1).getDay();
    return d === 0 ? 6 : d - 1;
  }

  _update() {
    if (!this._hass || !this._card) return;
    if (this._style) this._style.textContent = this._css();
    const isDark = !!(this._hass.themes?.darkMode);
    if (this.config?.card_style === 'pro') {
      const s = this.style;
      if (isDark) {
        s.setProperty('--p-bg', 'var(--ha-card-background, #1c1c1e)');
        s.setProperty('--p-surface', 'var(--secondary-background-color, #2c2c2e)');
        s.setProperty('--p-surface2', 'var(--ha-card-background, #232325)');
      } else {
        s.setProperty('--p-bg', '#FFFDF8');
        s.setProperty('--p-surface', '#FFF8EE');
        s.setProperty('--p-surface2', '#FFFCF5');
      }
    }
    if (this.config?.card_style === 'kline') {
      const s = this.style;
      if (isDark) {
        s.setProperty('--k-bg', 'var(--ha-card-background, #0a0a0f)');
        s.setProperty('--k-surface', 'rgba(255,255,255,0.04)');
        s.setProperty('--k-ink', 'rgba(255,255,255,0.85)');
        s.setProperty('--k-dim', 'rgba(255,255,255,0.3)');
        s.setProperty('--k-bdr', 'rgba(255,255,255,0.06)');
        s.setProperty('--k-chart-bg', 'rgba(0,0,0,0.3)');
        s.setProperty('--k-grid', 'rgba(255,255,255,0.04)');
        s.setProperty('--k-line-ji', '#22c55e');
        s.setProperty('--k-line-xiong', '#f43f5e');
        s.setProperty('--k-ticker-bg', 'rgba(0,0,0,0.5)');
        s.setProperty('--k-glow', 'rgba(99,102,241,0.05)');
        s.setProperty('--k-time-grad-start', 'rgba(255,255,255,0.9)');
        s.setProperty('--k-time-grad-end', 'rgba(255,255,255,0.15)');
        s.setProperty('--k-accent', '#c4b5fd');
      } else {
        s.setProperty('--k-bg', 'var(--ha-card-background, #ffffff)');
        s.setProperty('--k-surface', 'rgba(0,0,0,0.03)');
        s.setProperty('--k-ink', '#1a1a2e');
        s.setProperty('--k-dim', 'rgba(0,0,0,0.4)');
        s.setProperty('--k-bdr', 'rgba(0,0,0,0.08)');
        s.setProperty('--k-chart-bg', 'rgba(0,0,0,0.02)');
        s.setProperty('--k-grid', 'rgba(0,0,0,0.05)');
        s.setProperty('--k-line-ji', '#16a34a');
        s.setProperty('--k-line-xiong', '#dc2626');
        s.setProperty('--k-ticker-bg', 'rgba(0,0,0,0.03)');
        s.setProperty('--k-glow', 'rgba(99,102,241,0.03)');
        s.setProperty('--k-time-grad-start', 'rgba(0,0,0,0.85)');
        s.setProperty('--k-time-grad-end', 'rgba(0,0,0,0.2)');
        s.setProperty('--k-accent', '#7c3aed');
      }
    }

    const curDate = this._s("ri_qi");
    const weekday = this._s("xing_qi");
    const lunar = this._s("nong_li");
    const bazi = this._s("ba_zi");

    if (curDate === "N/A" || lunar === "N/A") {
      this._card.innerHTML = `<div class="error-msg">无法加载黄历数据<br><small>请检查传感器前缀: ${this._prefix}</small></div>`;
      return;
    }

    const curParts = curDate.split("-");
    const curDay = parseInt(curParts[2]);
    const curMonth = parseInt(curParts[1]) - 1;
    const curYear = parseInt(curParts[0]);
    const _now = new Date();
    const curTime = String(_now.getHours()).padStart(2,"0") + ":" + String(_now.getMinutes()).padStart(2,"0");

    if (!this._viewSynced) {
      this._viewDate = new Date(curYear, curMonth, 1);
      this._viewSynced = true;
    }

    const vY = this._viewDate.getFullYear();
    const vM = this._viewDate.getMonth();
    const daysInMonth = this._getMonthDays(vY, vM);
    const firstDay = this._getFirstDayOfWeek(vY, vM);
    const isCurrentMonth = (vY === curYear && vM === curMonth);

    const filteredLunar = lunar.replace(/^[^\s]+\s*/, "");
    const monthNames = ["一月","二月","三月","四月","五月","六月","七月","八月","九月","十月","十一月","十二月"];
    const cnDigits = ["〇","一","二","三","四","五","六","七","八","九"];
    const cnYear = String(vY).split("").map(d => cnDigits[parseInt(d)]).join("");
    const engMonths = ["January","February","March","April","May","June","July","August","September","October","November","December"];

    const zodiacMap = {"鼠":"Rat","牛":"Ox","虎":"Tiger","兔":"Rabbit","龙":"Dragon","蛇":"Snake","马":"Horse","羊":"Goat","猴":"Monkey","鸡":"Rooster","狗":"Dog","猪":"Pig"};
    const elemMap = {"甲":"Wood","乙":"Wood","丙":"Fire","丁":"Fire","戊":"Earth","己":"Earth","庚":"Metal","辛":"Metal","壬":"Water","癸":"Water"};
    const lunarMatch = lunar.match(/([^(（]+)[(（]([^)）]+)/);
    const ganzhiYear = lunarMatch ? lunarMatch[1] : (bazi !== "N/A" ? bazi.split(" ")[0] : "");
    const zodiacCn = lunarMatch ? lunarMatch[2] : "";
    const zodiacEn = zodiacMap[zodiacCn] || "";
    const elemEn = ganzhiYear ? (elemMap[ganzhiYear[0]] || "") : "";

    const jieqi = this._s("jie_qi");
    const jijie = this._s("ji_jie");
    const nayin = this._s("na_yin");
    const twelveGods = this._s("shi_er_shen");
    const fangwei = this._s("ji_shen_fang_wei");
    const fwMap = {};
    if (fangwei !== "N/A") {
      fangwei.split(/\s+/).forEach(item => { const m = item.match(/^(.{2})[:：]?(.+)$/); if (m) fwMap[m[1]] = m[2]; });
    }
    const jieri = this._s("jin_ri_jie_ri");
    const yi = this._s("yi");
    const ji = this._s("ji");
    const yiShort = yi !== "N/A" ? yi.split(/\s+/).slice(0, 3).join(" ") : "";
    const jiShort = ji !== "N/A" ? ji.split(/\s+/).slice(0, 3).join(" ") : "";
    const festivals = [];
    if (jieri && jieri !== "N/A" && this.config?.show_festivals) {
      jieri.split("（").forEach(item => { const t = item.replace(/）.*$/, "").trim(); if (t) festivals.push(t); });
    }

    const liuyao = this._s("liu_yao");
    const star = this._s("nian_ba_su");
    const xingci = this._s("xing_ci");
    const xingzuo = this._s("xing_zuo");
    const weekNo = this._s("zhou_shu");
    const moonPhase = this._s("yue_xiang");

    const dateParts = curDate.split("-");
    const dayNum = parseInt(dateParts[2]);
    const monthNum = parseInt(dateParts[1]);
    const shichen = this._s("shi_chen");

    let html = "";
    if (this.config?.card_style === "pro") {
      const feixing = this._s("jiu_gong_fei_xing");
      const xiongji = this._s("shi_chen_xiong_ji");
      const conflict = this._s("sheng_xiao_chong_sha");
      const fetusGod = this._s("jin_ri_tai_shen");
      const pengzu = this._s("peng_zu_bai_ji");
      const jishen = this._s("jin_ri_ji_shen");
      const evil = this._s("jin_ri_xiong_sha");
      const hexagram = this._s("liu_shi_si_gua");
      const yijidengdi = this._s("yi_ji_deng_di");
      const rilu = this._s("ri_lu");
      const meridian = this._s("shi_chen_jing_luo");
      const mangpai = this._s("mang_pai");
      const sanhe = this._s("jin_ri_san_he");
      const liuhe = this._s("jin_ri_liu_he");
      const sanshiliuqin = this._s("san_shi_liu_qin");
      const baziParts = bazi !== "N/A" ? bazi.split(" ") : ["--","--","--","--"];
      const yiItems = yi !== "N/A" ? yi.split(/\s+/).filter(Boolean) : [];
      const jiItems = ji !== "N/A" ? ji.split(/\s+/).filter(Boolean) : [];
      const comboStr = (liuhe !== "N/A" || sanhe !== "N/A") ? "" + [liuhe !== "N/A" ? liuhe : "", sanhe !== "N/A" ? sanhe : ""].join(" ").trim() : "";
      let pillars = [
        {name:"年柱",gz:baziParts[0],ny:""},
        {name:"月柱",gz:baziParts[1],ny:""},
        {name:"日柱",gz:baziParts[2],ny:""},
        {name:"时柱",gz:baziParts[3],ny:""}
      ];
      try {
        if (typeof LunarUtil !== "undefined" && LunarUtil.NAYIN) {
          pillars.forEach(p => { if (p.gz && p.gz !== "--") p.ny = LunarUtil.NAYIN[p.gz] || ""; });
        }
      } catch(e) {}
      html = `
      <div class="pro-wrap">
        <div class="pro-bar">
          <div class="pro-bar-l"><span class="pro-bar-date">${String(monthNum).padStart(2,"0")} / ${String(dayNum).padStart(2,"0")}</span> <span class="pro-bar-sep">|</span> ${weekday}</div>
          <div class="pro-bar-r">${moonPhase !== "N/A" ? moonPhase + " " : ""}${moonPhase !== "N/A" && xingzuo !== "N/A" ? '<span class="pro-bar-sep">|</span> ' : ''}${xingzuo !== "N/A" ? xingzuo + " " : ""}${weekNo !== "N/A" ? '<span class="pro-bar-wk">' + weekNo + '</span>' : ''}</div>
        </div>

        <div class="pro-main">
          <div class="pro-left">
            <div class="pro-lunar">${filteredLunar}</div>
            <div class="pro-season">${jieri !== "N/A" ? jieri : "\u6682\u65e0\u8282\u65e5"}</div>
            ${pengzu !== "N/A" ? '<div class="pro-grade"><span class="pro-grade-t">彭祖百忌</span><span class="pro-grade-body">' + pengzu + '</span></div>' : ''}
            ${yijidengdi !== "N/A" ? '<div class="pro-grade pro-grade-grn"><span class="pro-grade-t">宜忌等第</span><span class="pro-grade-body">' + yijidengdi + '</span></div>' : ''}
          </div>
          <div class="pro-right">
            <div class="pro-pillars">
              ${(() => { const wxc = {"甲":"#3A6B44","乙":"#6B9B7A","丙":"#9B2C27","丁":"#C45A55","戊":"#8B6914","己":"#B8A04A","庚":"#4A4A4A","辛":"#8C8A86","壬":"#3A4F6B","癸":"#6B8AAB"}; return pillars.map((p) => { const gz = p.gz || "--"; const t = gz[0] || "-"; const b = gz[1] || "-"; const c = wxc[t] || "#1A1A1A"; return '<div class="pro-pill"><div class="pro-pill-hd">' + p.name.replace("柱","") + '</div><div class="pro-pill-bd" style="color:' + c + '"><span>' + t + '</span><span>' + b + '</span></div>' + (p.ny ? '<div class="pro-pill-ny">' + p.ny + '</div>' : '') + '</div>'; }).join(""); })()}
            </div>
            <div class="pro-tags">${(() => { const tags = []; if (twelveGods !== "N/A") { const parts = twelveGods.split(/\s+/); if (parts[0]) tags.push('<span class="pro-tag pro-tag-red">' + parts[0] + '日</span>'); for (let i=1;i<parts.length;i++) if(parts[i]) tags.push('<span class="pro-tag pro-tag-gold">' + parts[i] + '</span>'); } if (liuyao !== "N/A") tags.push('<span class="pro-tag pro-tag-purple">' + liuyao + '</span>'); if (star !== "N/A") tags.push('<span class="pro-tag pro-tag-grn">' + star + '</span>'); if (xingci !== "N/A") tags.push('<span class="pro-tag pro-tag-blue">' + xingci + '</span>'); if (sanshiliuqin !== "N/A") tags.push('<span class="pro-tag pro-tag-gold">' + sanshiliuqin + '</span>'); return tags.join(''); })()}</div>
          </div>
        </div>

        <div class="pro-deities">
          ${[["财神",fwMap["财神"]],["喜神",fwMap["喜神"]],["福神",fwMap["福神"]],["阳贵",fwMap["阳贵"]||fwMap["贵人"]],["阴贵",fwMap["阴贵"]],["九星",feixing !== "N/A" ? feixing.split(" ")[0].replace(/星$/,"") : "-"]].map(d => '<div class="pro-deity"><span class="pro-deity-l">' + d[0] + '</span><span class="pro-deity-v">' + (d[1]||"-") + '</span></div>').join("")}
        </div>

        <div class="pro-micro">
          <div class="pro-micro-grid">
            <div class="pro-mi"><span class="pro-mi-l">生肖冲煞</span><span class="pro-mi-v pro-mi-red">${conflict !== "N/A" ? conflict : "-"}</span></div>
            <div class="pro-mi"><span class="pro-mi-l">时辰凶吉</span><span class="pro-mi-v pro-mi-red">${xiongji !== "N/A" ? xiongji : "-"}</span></div>
            <div class="pro-mi"><span class="pro-mi-l">盲派神煞</span><span class="pro-mi-v pro-mi-red">${mangpai !== "N/A" ? mangpai : "-"}</span></div>
            <div class="pro-mi"><span class="pro-mi-l">三六合化</span><span class="pro-mi-v pro-mi-red">${comboStr || "-"}</span></div>
          </div>
        </div>

      </div>`;
    } else if (this.config?.card_style === "kline") {
      const baziParts = bazi !== "N/A" ? bazi.split(" ") : ["--","--","--","--"];
      const yiItems = yi !== "N/A" ? yi.split(/\s+/).filter(Boolean).slice(0,5) : [];
      const jiItems = ji !== "N/A" ? ji.split(/\s+/).filter(Boolean).slice(0,5) : [];
      const conflict = this._s("sheng_xiao_chong_sha");
      const feixing = this._s("jiu_gong_fei_xing");
      const hexagram = this._s("liu_shi_si_gua");
      const jishen = this._s("jin_ri_ji_shen");
      const evil = this._s("jin_ri_xiong_sha");
      const fetusGod = this._s("jin_ri_tai_shen");
      const pengzu = this._s("peng_zu_bai_ji");
      const meridian = this._s("shi_chen_jing_luo");
      const xiongjiAttr = this._sa("shi_chen_xiong_ji");
      const scKeys = ["23-01","01-03","03-05","05-07","07-09","09-11","11-13","13-15","15-17","17-19","19-21","21-23"];
      const scNames = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"];
      const tgWx = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"};
      const tgYang = {"甲":1,"丙":1,"戊":1,"庚":1,"壬":1,"乙":0,"丁":0,"己":0,"辛":0,"癸":0};
      const dzWx = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"};
      const dzYang = {子:1,寅:1,辰:1,午:1,申:1,戌:1,丑:0,卯:0,巳:0,未:0,酉:0,亥:0};
      const dzCangGan = {
        子:[{wx:"水",w:1}],
        丑:[{wx:"土",w:.6},{wx:"水",w:.25},{wx:"金",w:.15}],
        寅:[{wx:"木",w:.6},{wx:"火",w:.3},{wx:"土",w:.1}],
        卯:[{wx:"木",w:1}],
        辰:[{wx:"土",w:.6},{wx:"木",w:.25},{wx:"水",w:.15}],
        巳:[{wx:"火",w:.6},{wx:"金",w:.3},{wx:"土",w:.1}],
        午:[{wx:"火",w:.65},{wx:"土",w:.35}],
        未:[{wx:"土",w:.6},{wx:"火",w:.25},{wx:"木",w:.15}],
        申:[{wx:"金",w:.6},{wx:"水",w:.3},{wx:"土",w:.1}],
        酉:[{wx:"金",w:1}],
        戌:[{wx:"土",w:.6},{wx:"金",w:.25},{wx:"火",w:.15}],
        亥:[{wx:"水",w:.65},{wx:"木",w:.35}]
      };
      const scVitality = {子:.7,丑:.6,寅:.85,卯:.95,辰:1,巳:1.1,午:1.2,未:1,申:.9,酉:.8,戌:.7,亥:.65};
      const wxCount = {木:0,火:0,土:0,金:0,水:0};
      baziParts.forEach(gz => {
        if (!gz || gz === "--" || gz.length < 2) return;
        if (tgWx[gz[0]]) wxCount[tgWx[gz[0]]]++;
        if (dzWx[gz[1]]) wxCount[dzWx[gz[1]]]++;
      });
      const wxArr = [{n:"木",c:"#22c55e"},{n:"火",c:"#ef4444"},{n:"土",c:"#eab308"},{n:"金",c:"#a1a1aa"},{n:"水",c:"#3b82f6"}];
      const dominant = wxArr.reduce((a,b) => wxCount[a.n] >= wxCount[b.n] ? a : b);
      const dayGz = baziParts[2] || "--";
      const dayMaster = dayGz.length >= 1 ? (tgWx[dayGz[0]] || "土") : "土";
      const dayIsYang = dayGz.length >= 1 ? (tgYang[dayGz[0]] ?? 1) : 1;
      const shengWo = {木:"水",火:"木",土:"火",金:"土",水:"金"};
      const keWo = {木:"金",火:"水",土:"木",金:"火",水:"土"};
      const woSheng = {木:"火",火:"土",土:"金",金:"水",水:"木"};
      const woKe = {木:"土",火:"金",土:"水",金:"木",水:"火"};
      const wxRel = (me, other) => {
        if (me === other) return 12;
        if (shengWo[me] === other) return 16;
        if (woSheng[me] === other) return 4;
        if (woKe[me] === other) return 1;
        if (keWo[me] === other) return -13;
        return 0;
      };
      const nowH = new Date().getHours();
      const curScIdx = nowH === 23 ? 0 : nowH < 1 ? 0 : nowH < 3 ? 1 : nowH < 5 ? 2 : nowH < 7 ? 3 : nowH < 9 ? 4 : nowH < 11 ? 5 : nowH < 13 ? 6 : nowH < 15 ? 7 : nowH < 17 ? 8 : nowH < 19 ? 9 : nowH < 21 ? 10 : 11;
      const scData = scKeys.map((k, i) => {
        const v = xiongjiAttr[k];
        const isJi = v === "吉";
        const dz = scNames[i];
        const cg = dzCangGan[dz] || [{wx:"土",w:1}];
        let relBase = 0;
        cg.forEach(g => { relBase += wxRel(dayMaster, g.wx) * g.w; });
        const vit = scVitality[dz] || 1;
        const yinYangBonus = (dayIsYang === dzYang[dz]) ? 2 : -1;
        const jiGrade = isJi ? (relBase > 5 ? 18 : relBase > 0 ? 14 : 10) : (relBase < -5 ? -18 : relBase < 0 ? -14 : -8);
        const score = Math.round(50 + relBase * vit + yinYangBonus + jiGrade);
        return { key: k, name: dz, isJi, isCur: i === curScIdx, score };
      });
      const jiCnt = scData.filter(d => d.isJi).length;
      const xiongCnt = 12 - jiCnt;
      const kUp = jiCnt >= xiongCnt;
      const curSc = scData[curScIdx];
      const scores = scData.map(d => d.score);
      const sMin = Math.min(...scores);
      const sMax = Math.max(...scores);
      const sRange = sMax - sMin || 1;
      const svgW = 300, svgH = 80, padX = 8, padY = 6;
      const chartW = svgW - padX * 2, chartH = svgH - padY * 2;
      const pts = scData.map((d, i) => {
        const x = padX + (i / 11) * chartW;
        const y = padY + (1 - (d.score - sMin) / sRange) * chartH;
        return { x: +x.toFixed(1), y: +y.toFixed(1), d };
      });
      const polyline = pts.map(p => p.x + "," + p.y).join(" ");
      const areaPath = "M" + pts[0].x + "," + (svgH - padY) + " L" + pts.map(p => p.x + "," + p.y).join(" L") + " L" + pts[11].x + "," + (svgH - padY) + " Z";
      const curPt = pts[curScIdx];
      const kPillars = [{label:"年柱",gz:baziParts[0]},{label:"月柱",gz:baziParts[1]},{label:"日柱",gz:baziParts[2]},{label:"时柱",gz:baziParts[3]}];
      html = `
      <div class="k-wrap">
        <div class="k-ticker">${(()=>{
          const ti = [];
          ti.push('<span class="k-tk-' + (kUp?'ok':'warn') + '">◈ ' + (kUp?'吉日':'凶日') + ' ' + jiCnt + '吉' + xiongCnt + '凶</span>');
          ti.push('<span>' + filteredLunar + '</span>');
          if (jieqi !== 'N/A') ti.push('<span>' + jieqi + '</span>');
          if (nayin !== 'N/A') ti.push('<span>纳音 ' + nayin + '</span>');
          if (twelveGods !== 'N/A') ti.push('<span>建除 ' + twelveGods + '</span>');
          if (jishen !== 'N/A') ti.push('<span class="k-tk-ok">吉神 ' + jishen.split(/\s+/).slice(0,3).join(' ') + '</span>');
          if (evil !== 'N/A') ti.push('<span class="k-tk-warn">凶煞 ' + evil.split(/\s+/).slice(0,3).join(' ') + '</span>');
          if (conflict !== 'N/A') ti.push('<span>冲煞 ' + conflict + '</span>');
          if (feixing !== 'N/A') ti.push('<span>飞星 ' + feixing.split(' ')[0] + '</span>');
          if (hexagram !== 'N/A') ti.push('<span>卦象 ' + hexagram + '</span>');
          if (fetusGod !== 'N/A') ti.push('<span>胎神 ' + fetusGod + '</span>');
          if (pengzu !== 'N/A') ti.push('<span>彭祖 ' + pengzu.substring(0,8) + '</span>');
          if (meridian !== 'N/A') ti.push('<span>经络 ' + meridian + '</span>');
          if (star !== 'N/A') ti.push('<span>值星 ' + star + '</span>');
          ti.push('<span>' + weekday + ' · ' + curDate + '</span>');
          ti.push('<span class="k-tk-' + (curSc.isJi?'ok':'warn') + '">◈ ' + curSc.name + '时 ' + (curSc.isJi?'吉':'凶') + '</span>');
          const block = ti.join('');
          return '<div class="k-ticker-a">' + block + '</div><div class="k-ticker-b" aria-hidden="true">' + block + '</div>';
        })()}</div>
        <div class="k-head">
          <div class="k-head-l">
            <div class="k-time">${curTime}</div>
            <div class="k-status">
              <span class="k-status-sub">${filteredLunar}</span>
              <span class="k-dot ${curSc.isJi?"k-dot-g":"k-dot-r"}"></span>
              <span class="k-status-t">${curSc.name}时 · ${curSc.isJi?"吉":"凶"}</span>
            </div>
          </div>
          <div class="k-head-r">
            <div class="k-score">${curSc.score}</div>
            <div class="k-score-label">运势指数</div>
          </div>
        </div>
        <div class="k-body">
          <div class="k-chart-hd">
            <span class="k-chart-title">十二时辰走势</span>
            <span class="k-chart-ratio"><span class="k-ratio-ji">${jiCnt}吉</span> <span class="k-ratio-xiong">${xiongCnt}凶</span> · 主气${dominant.n}</span>
          </div>
          <div class="k-chart">
            <svg viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="none" class="k-svg">
              <defs>
                <linearGradient id="kGradG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="var(--k-line-ji,#22c55e)" stop-opacity="0.25"/>
                  <stop offset="100%" stop-color="var(--k-line-ji,#22c55e)" stop-opacity="0"/>
                </linearGradient>
                <linearGradient id="kGradR" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="var(--k-line-xiong,#f43f5e)" stop-opacity="0.2"/>
                  <stop offset="100%" stop-color="var(--k-line-xiong,#f43f5e)" stop-opacity="0"/>
                </linearGradient>
              </defs>
              <line x1="${padX}" y1="${svgH/2}" x2="${svgW-padX}" y2="${svgH/2}" stroke="var(--k-grid,rgba(255,255,255,0.04))" stroke-width="0.5" stroke-dasharray="3 3"/>
              ${pts.map((p, idx) => {
                if (idx === 0) return '';
                const prev = pts[idx - 1];
                const midX = (prev.x + p.x) / 2;
                const bot = svgH - padY;
                const grad = p.d.isJi ? 'url(#kGradG)' : 'url(#kGradR)';
                return '<path d="M' + midX + ',' + bot + ' L' + prev.x + ',' + prev.y + ' L' + p.x + ',' + p.y + ' L' + (idx < 11 ? ((p.x + pts[idx+1].x)/2) : p.x) + ',' + bot + ' Z" fill="' + grad + '"/>';
              }).join('')}
              ${pts.map((p, idx) => {
                if (idx === 0) return '';
                const prev = pts[idx - 1];
                const col = p.d.isJi ? 'var(--k-line-ji,#22c55e)' : 'var(--k-line-xiong,#f43f5e)';
                return '<line x1="' + prev.x + '" y1="' + prev.y + '" x2="' + p.x + '" y2="' + p.y + '" stroke="' + col + '" stroke-width="2" stroke-linecap="round"/>';
              }).join('')}
            </svg>
            <div class="k-dots">
              ${pts.map(p => {
                const lPct = (p.x / svgW * 100).toFixed(1);
                const tPct = (p.y / svgH * 100).toFixed(1);
                const color = p.d.isJi ? 'var(--k-line-ji,#22c55e)' : 'var(--k-line-xiong,#f43f5e)';
                const cls = 'k-pt' + (p.d.isCur ? ' k-pt-cur' : '');
                return '<span class="' + cls + '" style="left:' + lPct + '%;top:' + tPct + '%;background:' + color + '"></span>';
              }).join('')}
            </div>
            <div class="k-x-axis">
              ${pts.map(p => '<span class="k-x-label' + (p.d.isCur ? " k-x-cur" : "") + '" style="left:' + (p.x / svgW * 100).toFixed(1) + '%">' + p.d.name + '</span>').join("")}
            </div>
          </div>
          <div class="k-wx-bar">
            ${wxArr.map(w => '<span class="k-wx-item"><span class="k-wx-dot" style="background:' + w.c + '"></span>' + w.n + " " + wxCount[w.n] + '</span>').join("")}
          </div>
          <div class="k-pillars">
            ${kPillars.map(p => {
              const gz = p.gz || "--";
              return '<div class="k-pill"><span class="k-pill-label">' + p.label + '</span><span class="k-pill-gz">' + gz + '</span></div>';
            }).join("")}
          </div>
        </div>
        <div class="k-bottom">
          <div class="k-yiji">
            <div class="k-yi">
              <div class="k-yi-hd"><span class="k-yi-dot k-yi-dot-g"></span>宜</div>
              <div class="k-yi-bd k-yi-bd-g">${yiItems.join(" · ") || "—"}</div>
            </div>
            <div class="k-yi">
              <div class="k-yi-hd"><span class="k-yi-dot k-yi-dot-r"></span>忌</div>
              <div class="k-yi-bd k-yi-bd-r">${jiItems.join(" · ") || "—"}</div>
            </div>
          </div>
        </div>
      </div>`;
    } else {
      html = `
      <div class="calendar-wrap">
        <div class="cal-bar">
          <div class="cal-bar-l">${shichen !== "N/A" ? shichen : weekday}${jieri !== "N/A" ? ' <span class="cal-fest">' + jieri + '</span>' : ""}</div>
          <div class="cal-bar-r">${moonPhase !== "N/A" ? moonPhase : ""}${moonPhase !== "N/A" && xingzuo !== "N/A" ? " · " : ""}${xingzuo !== "N/A" ? xingzuo : ""}${(moonPhase !== "N/A" || xingzuo !== "N/A") && weekNo !== "N/A" ? " · " : ""}${weekNo !== "N/A" ? weekNo : ""}</div>
        </div>

        <div class="cal-weekdays">
          ${["一","二","三","四","五","六","日"].map((d,i) => `<div class="cal-wd${i>=5?' cal-wd-weekend':''}">${d}</div>`).join("")}
        </div>

        <div class="cal-grid">
          ${(() => {
            const prevY = vM === 0 ? vY - 1 : vY;
            const prevM = vM === 0 ? 11 : vM - 1;
            const prevMonthDays = this._getMonthDays(prevY, prevM);
            const nextY = vM === 11 ? vY + 1 : vY;
            const nextM = vM === 11 ? 0 : vM + 1;
            const totalCells = 35;
            let cellCount = 0;
            let cells = "";
            for (let i = 0; i < firstDay && cellCount < totalCells; i++, cellCount++) {
              const d = prevMonthDays - firstDay + 1 + i;
              const ld = _getLunarDay(prevY, prevM + 1, d);
              cells += `<div class="day-cell day-other" data-day="${d}" data-year="${prevY}" data-month="${prevM+1}"><span class="day-num day-num-other">${d}</span><span class="day-lunar day-lunar-other${ld.special ? ' day-lunar-special' : ''}">${ld.text}</span></div>`;
            }
            for (let d = 1; d <= daysInMonth && cellCount < totalCells; d++, cellCount++) {
              const isActive = isCurrentMonth && d === curDay;
              const ld = _getLunarDay(vY, vM + 1, d);
              cells += `
                <div class="day-cell${isActive ? ' day-active' : ''}" data-day="${d}">
                  <span class="day-num">${d}</span>
                  <span class="day-lunar${ld.special ? ' day-lunar-special' : ''}">${ld.text}</span>
                  ${isActive ? '<div class="day-dot"></div>' : ''}
                </div>`;
            }
            for (let d = 1; cellCount < totalCells; d++, cellCount++) {
              const ld = _getLunarDay(nextY, nextM + 1, d);
              cells += `<div class="day-cell day-other" data-day="${d}" data-year="${nextY}" data-month="${nextM+1}"><span class="day-num day-num-other">${d}</span><span class="day-lunar day-lunar-other${ld.special ? ' day-lunar-special' : ''}">${ld.text}</span></div>`;
            }
            return cells;
          })()}
        </div>

        <div class="cal-nav">
          <button class="month-prev"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6"/></svg></button>
          <span class="cal-nav-label">${cnYear}年 <b>${monthNames[vM]}</b></span>
          <button class="month-next"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg></button>
        </div>

      </div>`;
    }

    if (this.config?.card_style === "kline") {
      const klineKey = html.replace(/<div class="k-time">[^<]*<\/div>/, "");
      if (this._lastKlineKey !== klineKey) {
        this._lastKlineKey = klineKey;
        this._card.innerHTML = html;
        requestAnimationFrame(() => {
          const a = this._card.querySelector(".k-ticker-a");
          if (a) {
            const w = a.scrollWidth;
            const ticker = this._card.querySelector(".k-ticker");
            if (ticker) ticker.style.setProperty("--tk-w", w + "px");
          }
        });
      } else {
        const el = this._card.querySelector(".k-time");
        if (el) { const _n = new Date(); el.textContent = String(_n.getHours()).padStart(2,"0") + ":" + String(_n.getMinutes()).padStart(2,"0"); }
      }
    } else {
      this._card.innerHTML = html;
    }

    if (this._detailOpen && !this._overlayEl) {
      this._showDetailOverlay({ curDate, weekday, filteredLunar, lunar, bazi, jieqi, festivals });
    }
  }

  _renderDetail({ curDate, weekday, filteredLunar, lunar, bazi, jieqi, festivals }) {
    const bp = bazi.split(" ");
    const fw = this._s("ji_shen_fang_wei");
    const fwMap = {};
    if (fw !== "N/A") fw.split(/\s+/).forEach(item => { const m = item.match(/^(.{2})[:：]?(.+)$/); if (m) fwMap[m[1]] = m[2]; });
    const feixing = this._s("jiu_gong_fei_xing");
    const shichen = this._s("shi_chen");
    const xiongji = this._s("shi_chen_xiong_ji");
    const xiongjiAttrs = this._sa("shi_chen_xiong_ji");
    const jijie = this._s("ji_jie");
    const yi = this._s("yi");
    const ji = this._s("ji");
    const yiArr = (yi !== "N/A" ? yi.split(/\s+/).filter(Boolean) : []).slice(0,5);
    const jiArr = (ji !== "N/A" ? ji.split(/\s+/).filter(Boolean) : []).slice(0,5);
    const pengzu = this._s("peng_zu_bai_ji");
    const evil = this._s("jin_ri_xiong_sha");
    const nayin = this._s("na_yin");
    const star = this._s("nian_ba_su");
    const conflict = this._s("sheng_xiao_chong_sha");
    const twelveGods = this._s("shi_er_shen");
    const liuyao = this._s("liu_yao");
    const xingzuo = this._s("xing_zuo");
    const fetusGod = this._s("jin_ri_tai_shen");
    const hexagram = this._s("liu_shi_si_gua");
    const fxAttrs = this._sa("jiu_gong_fei_xing");
    const v = (s) => s !== "N/A" && s ? s : "-";
    const fxParts = feixing !== "N/A" ? feixing.split(/\s+/) : [];
    const lunarMatch = lunar ? lunar.match(/([^(（\s]+)[(（]([^)）]+)/) : null;
    const ganzhiYear = lunarMatch ? lunarMatch[1] : (bp[0] || "");
    const zodiacCn = lunarMatch ? lunarMatch[2] : "";
    const dateParts = curDate.split("-");
    const dayNum = dateParts[2] || "";
    const monthNames = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const monthAbbr = monthNames[parseInt(dateParts[1],10)] || "";
    const pzParts = pengzu !== "N/A" ? pengzu.split(/\s+/) : ["-"];
    const pillar = (label, chars, hl) => {
      const c0 = chars ? chars[0] : "-";
      const c1 = chars ? chars[1] : "-";
      return `<div class="dp-pl${hl ? ' dp-pl-hl' : ''}"><span class="dp-pl-lb">${label}</span><div class="dp-pl-ch"><span class="${hl ? 'dp-pl-r' : 'dp-pl-d'}">${c0}</span><span class="dp-pl-s">${c1}</span></div></div>`;
    };

    return `<div class="dp">
      <div class="dp-top">
        <span class="dp-top-t">ALMANAC ${dateParts[0] || "2026"}</span>
        <button class="dp-close"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg></button>
      </div>
      <div class="dp-scroll">
        <div class="dp-date">
          <div class="dp-date-l">
            ${jieqi && jieqi !== "N/A" ? '<div class="dp-term">' + jieqi + '</div>' : ''}
            <h1 class="dp-lunar">${filteredLunar}</h1>
            <div class="dp-meta">
              <span>${ganzhiYear}${zodiacCn ? "(" + zodiacCn + ")" : ""}年</span>
              <span class="dp-meta-sep"></span>
              <span>${curDate}</span>
              <span class="dp-meta-sep"></span>
              <span>${weekday}</span>
            </div>
          </div>
          <div class="dp-date-r">
            <span class="dp-date-mon">${monthAbbr}</span>
            <span class="dp-date-day">${dayNum}</span>
          </div>
        </div>
        <div class="dp-yiji">
          <div class="dp-yj-row">
            <div class="dp-yj-dot dp-dot-g">宜</div>
            <div class="dp-yj-items">${yiArr.map(i => '<span class="dp-yj-tag dp-yi-tag">' + i + '</span>').join("")}</div>
          </div>
          <div class="dp-yj-row">
            <div class="dp-yj-dot dp-dot-r">忌</div>
            <div class="dp-yj-items">${jiArr.map(i => '<span class="dp-yj-tag dp-ji-tag">' + i + '</span>').join("")}</div>
          </div>
        </div>
        <div class="dp-bazi">
          ${pillar("Year", bp[0], false)}
          ${pillar("Month", bp[1], false)}
          ${pillar("Day", bp[2], true)}
          ${pillar("Time", bp[3], false)}
        </div>
        <div class="dp-tags">
          <div class="dp-tag-i"><span class="dp-tag-lb">星宿</span><span class="dp-tag-val">${v(star)}</span></div>
          <div class="dp-tag-i"><span class="dp-tag-lb">纳音</span><span class="dp-tag-val">${v(nayin)}</span></div>
          <div class="dp-tag-i"><span class="dp-tag-lb">十二神</span><span class="dp-tag-val">${v(twelveGods)}</span></div>
          <div class="dp-tag-i"><span class="dp-tag-lb">冲煞</span><span class="dp-tag-val dp-tag-red">${v(conflict)}</span></div>
          <div class="dp-tag-i"><span class="dp-tag-lb">六曜</span><span class="dp-tag-val">${v(liuyao)}</span></div>
          <div class="dp-tag-i"><span class="dp-tag-lb">星座</span><span class="dp-tag-val">${v(xingzuo)}</span></div>
          <div class="dp-tag-i"><span class="dp-tag-lb">胎神</span><span class="dp-tag-val">${v(fetusGod)}</span></div>
          <div class="dp-tag-i"><span class="dp-tag-lb">彭祖</span><span class="dp-tag-val">${pzParts[0] || "-"}</span></div>
        </div>
        <div class="dp-panel">
          <div class="dp-panel-top">
            <div class="dp-panel-l">
              <h3 class="dp-sec-t">I Ching · 卦象</h3>
              ${(() => {
                const hx = v(hexagram);
                if (hx === '-' || !hx.includes('=>')) return '<div class="dp-gua-text">' + hx + '</div>';
                const [origName, changeName] = hx.split('=>').map(s => s.trim());
                const tri = {乾:[1,1,1],兑:[1,1,0],离:[1,0,1],震:[1,0,0],巽:[0,1,1],坎:[0,1,0],艮:[0,0,1],坤:[0,0,0]};
                const guaMap = {};
                const names64 = [
                  ['乾','乾','乾'],['乾','兑','夬'],['乾','离','大有'],['乾','震','大壮'],['乾','巽','小畜'],['乾','坎','需'],['乾','艮','大畜'],['乾','坤','泰'],
                  ['兑','乾','履'],['兑','兑','兑'],['兑','离','睽'],['兑','震','归妹'],['兑','巽','中孚'],['兑','坎','节'],['兑','艮','损'],['兑','坤','临'],
                  ['离','乾','同人'],['离','兑','革'],['离','离','离'],['离','震','丰'],['离','巽','家人'],['离','坎','既济'],['离','艮','贲'],['离','坤','明夷'],
                  ['震','乾','无妄'],['震','兑','随'],['震','离','噬嗑'],['震','震','震'],['震','巽','益'],['震','坎','屯'],['震','艮','颐'],['震','坤','复'],
                  ['巽','乾','姤'],['巽','兑','大过'],['巽','离','鼎'],['巽','震','恒'],['巽','巽','巽'],['巽','坎','井'],['巽','艮','蛊'],['巽','坤','升'],
                  ['坎','乾','讼'],['坎','兑','困'],['坎','离','未济'],['坎','震','解'],['坎','巽','涣'],['坎','坎','坎'],['坎','艮','蒙'],['坎','坤','师'],
                  ['艮','乾','遁'],['艮','兑','咸'],['艮','离','旅'],['艮','震','小过'],['艮','巽','渐'],['艮','坎','蹇'],['艮','艮','艮'],['艮','坤','谦'],
                  ['坤','乾','否'],['坤','兑','萃'],['坤','离','晋'],['坤','震','豫'],['坤','巽','观'],['坤','坎','比'],['坤','艮','剥'],['坤','坤','坤']
                ];
                names64.forEach(([up,dn,nm]) => { guaMap[nm+'卦'] = [...tri[up],...tri[dn]]; guaMap[nm] = [...tri[up],...tri[dn]]; });
                const origYao = guaMap[origName] || null;
                const changeYao = guaMap[changeName] || null;
                if (!origYao && !changeYao) return '<div class="dp-gua-text">' + hx + '</div>';
                const drawYao = (yao) => {
                  return yao.map((y, i) => {
                    const yOff = 4 + i * 7;
                    if (y === 1) return '<line x1="4" y1="' + yOff + '" x2="32" y2="' + yOff + '" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>';
                    return '<line x1="4" y1="' + yOff + '" x2="15" y2="' + yOff + '" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><line x1="21" y1="' + yOff + '" x2="32" y2="' + yOff + '" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>';
                  }).join('');
                };
                const origSvg = origYao ? '<svg viewBox="0 0 36 46" class="dp-gua-svg">' + drawYao(origYao) + '</svg>' : '';
                const changeSvg = changeYao ? '<svg viewBox="0 0 36 46" class="dp-gua-svg">' + drawYao(changeYao) + '</svg>' : '';
                return '<div class="dp-gua-row">' +
                  '<div class="dp-gua-item">' + origSvg + '<span class="dp-gua-name">' + origName + '</span></div>' +
                  '<span class="dp-gua-arrow">⇒</span>' +
                  '<div class="dp-gua-item">' + changeSvg + '<span class="dp-gua-name">' + changeName + '</span></div>' +
                  '</div>';
              })()}
            </div>
            <div class="dp-panel-r">
              <h3 class="dp-sec-t">Compass · 方位</h3>
              <div class="dp-compass-wrap">
                <div class="dp-compass-ring">
                  <div class="dp-compass-inner"></div>
                  <div class="dp-compass-cross-h"></div>
                  <div class="dp-compass-cross-v"></div>
                  <span class="dp-dir dp-dir-n">北</span>
                  <span class="dp-dir dp-dir-s">南</span>
                  <span class="dp-dir dp-dir-w">西</span>
                  <span class="dp-dir dp-dir-e">东</span>
                  <div class="dp-compass-center">
                    <span class="dp-cc-r">财 ${fwMap["财神"] || "-"}</span>
                    <span class="dp-cc-g">喜 ${fwMap["喜神"] || "-"}</span>
                  </div>
                </div>
              </div>
              <div class="dp-compass-meta">
                <span>福神 ${fwMap["福神"] || "-"}</span>
                <span>阳贵 ${fwMap["阳贵"] || fwMap["贵人"] || "-"}</span>
              </div>
            </div>
          </div>
          <div class="dp-panel-bot">
            <h3 class="dp-sec-t">Nine Star · 飞星</h3>
            ${(() => {
              const pos = ['东南','正南','西南','正东','中宫','正西','东北','正北','西北'];
              const gua = ['巽','离','坤','震','','兑','艮','坎','乾'];
              const hasData = fxAttrs && Object.keys(fxAttrs).length > 0;
              const colorMap = {'白':'#78716c','黑':'#1c1917','碧':'#166534','绿':'#15803d','黄':'#a16207','赤':'#dc2626','紫':'#7e22ce'};
              if (!hasData) return '<div class="dp-fx-state">' + v(feixing) + '</div>';
              const cells = pos.map((p, i) => {
                const raw = fxAttrs[p] || '';
                const numMatch = raw.match(/(\d)/);
                const num = numMatch ? numMatch[1] : '?';
                const colorSuffix = raw.slice(-1);
                const c = colorMap[colorSuffix] || '#78716c';
                const isCenter = i === 4;
                return '<div class="dp-fx-cell' + (isCenter ? ' dp-fx-center' : '') + '"><span class="dp-fx-num" style="color:' + c + '">' + num + '</span><span class="dp-fx-pos">' + (gua[i] || p) + '</span></div>';
              });
              return '<div class="dp-fx-grid">' + cells.join('') + '</div><div class="dp-fx-state">' + v(feixing) + '</div>';
            })()}
          </div>
        </div>
        ${(() => {
          const scNames = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'];
          const scRanges = ['23-01','01-03','03-05','05-07','07-09','09-11','11-13','13-15','15-17','17-19','19-21','21-23'];
          const hasData = xiongjiAttrs && Object.keys(xiongjiAttrs).length > 0;
          if (!hasData) return '';
          const nowH = new Date().getHours();
          const curIdx = nowH === 23 ? 0 : Math.floor((nowH + 1) / 2) % 12;
          const cells = scNames.map((n, i) => {
            const val = xiongjiAttrs[scRanges[i]] || '';
            const isJi = val === '吉';
            const isCur = i === curIdx;
            return '<div class="dp-sc' + (isCur ? ' dp-sc-cur' : '') + '"><span class="dp-sc-name">' + n + '</span><span class="dp-sc-val' + (isJi ? ' dp-sc-ji' : ' dp-sc-xiong') + '">' + (isJi ? '吉' : '凶') + '</span></div>';
          });
          return '<div class="dp-shichen"><h3 class="dp-sec-t2">Twelve Hours · ' + v(shichen) + '</h3><div class="dp-sc-grid">' + cells.join('') + '</div></div>';
        })()}
        <div class="dp-evil">
          <span class="dp-evil-lb">Evil Spirits</span>
          <p class="dp-evil-v">${v(evil)}</p>
        </div>
      </div>
      <div class="dp-bottom-bar"><div class="dp-bb-r"></div><div class="dp-bb-g"></div><div class="dp-bb-d"></div></div>
    </div>`;
  }

  _css() {
    return `
:host {
  --c-red: var(--primary-color, #d94a43);
  --c-ink: var(--primary-text-color, #1a1a1a);
  --c-dim: var(--secondary-text-color, #777);
  --c-bg: var(--card-background-color, var(--ha-card-background, #ffffff));
  --c-gold: var(--accent-color, #f5a623);
  --c-bdr: var(--divider-color, rgba(0,0,0,0.05));
  --c-grn: #22c55e;
  --c-paper: var(--card-background-color, var(--ha-card-background, #fafaf8));
  --f-cn: var(--ha-card-header-font-family, -apple-system, "Helvetica Neue", sans-serif);
  --f-grid: "FZCuSong","Noto Serif SC","Songti SC",serif;
  --p-bg: var(--ha-card-background, #FCFAF5);
  --p-bar: var(--ha-card-header-color, #3A3835);
  --p-bar-text: var(--text-primary-color, #FAFAFA);
  --p-ink: var(--primary-text-color, #1A1A1A);
  --p-dim: var(--secondary-text-color, #6E6C68);
  --p-dim2: var(--secondary-text-color, #A0A09C);
  --p-mute: var(--secondary-text-color, #8C8A86);
  --p-mute2: var(--secondary-text-color, #888179);
  --p-surface: var(--secondary-background-color, #F5F2EB);
  --p-surface2: var(--ha-card-background, #FAF8F3);
  --p-border: var(--divider-color, #E8E4DA);
  --p-border2: var(--divider-color, #E5E3DE);
  --p-red: #D04A42;
  --p-grn: #2E8B57;
  --p-gold: #D4A017;
  --p-blue: #4682B4;
  --p-purple: #7B5EA7;
  --k-bg: #050508;
  --k-surface: rgba(255,255,255,0.05);
  --k-ink: rgba(255,255,255,0.85);
  --k-dim: rgba(255,255,255,0.35);
  --k-bdr: rgba(255,255,255,0.06);
}
ha-card {
  background: var(--c-paper);
  color: var(--c-ink);
  border-radius: var(--ha-card-border-radius, 12px);
  box-shadow: none;
  font-family: var(--f-cn);
  overflow: hidden; position: relative;
  border: 1px solid var(--ha-card-border-color, var(--c-bdr));
}
.error-msg { padding: 24px; text-align: center; color: var(--c-dim); font-size: 13px; }

/* ===== CALENDAR GRID ===== */
.calendar-wrap { display: flex; flex-direction: column; }
.cal-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 16px; background: var(--c-bg); border-bottom: 1px solid var(--c-bdr);
}
.cal-bar-l { font-size: 13px; font-weight: 600; color: var(--c-ink); font-family: serif; letter-spacing: 1px; }
.cal-fest { font-size: 11px; color: #C0443E; border: 1px solid rgba(192,68,62,0.3); border-radius: 3px; padding: 1px 6px; margin-left: 6px; font-weight: 700; letter-spacing: 1px; }
.cal-bar-r { font-size: 12px; color: var(--c-dim); letter-spacing: 1px; }

.cal-header { display: flex; flex-direction: column; border-bottom: 1px solid var(--c-bdr); background: var(--c-bg); }
.cal-mid {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px;
}
.cal-mid-l { }
.cal-lunar {
  font-size: 22px; color: var(--c-ink); font-weight: 700; line-height: 1.2;
  font-family: "Noto Serif SC","Songti SC",serif;
}
.cal-bz {
  font-size: 12px; color: var(--c-dim); letter-spacing: 0.5px; margin-top: 4px;
  font-family: "Noto Serif SC","Songti SC",serif;
}
.cal-mid-r {
  text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px;
  flex-shrink: 0;
}
.cal-r1 { font-size: 13px; color: var(--c-ink); letter-spacing: 0.5px; font-weight: 600; }
.cal-r2 { font-size: 12px; color: var(--c-dim); letter-spacing: 0.5px; display: flex; align-items: center; gap: 5px; }
.cal-tag {
  font-size: 10px; font-weight: 700; color: var(--c-ink); background: var(--c-bdr);
  padding: 1px 5px; border-radius: 2px; letter-spacing: 1px;
}

.cal-weekdays {
  display: grid; grid-template-columns: repeat(7, 1fr);
  border-top: 1px solid rgba(0,0,0,0.04); border-left: 1px solid rgba(0,0,0,0.04);
  background: var(--c-paper);
}
.cal-wd {
  text-align: center; padding: 7px 0; font-size: 10px;
  font-family: -apple-system,sans-serif; font-weight: 700;
  color: var(--c-dim); letter-spacing: 1px;
  border-right: 1px solid var(--c-bdr); border-bottom: 1px solid var(--c-bdr);
}
.cal-wd-weekend { color: #d94a43 !important; }

.cal-grid {
  display: grid; grid-template-columns: repeat(7, 1fr);
  border-left: 1px solid rgba(0,0,0,0.04);
  background: var(--c-bg);
}
.day-cell {
  height: 48px; border-right: 1px solid var(--c-bdr); border-bottom: 1px solid var(--c-bdr);
  padding: 2px; display: flex; flex-direction: column; align-items: center; justify-content: center;
  cursor: pointer; position: relative; transition: background 0.15s;
  background: var(--c-bg); min-height: 0; gap: 0; text-align: center; overflow: hidden;
}
.day-cell:hover { background: var(--c-bdr); }
.day-other { background: var(--c-paper); cursor: default; }
.day-num-other { color: var(--c-dim) !important; opacity: 0.4 !important; font-weight: 400 !important; }
.day-lunar-other { color: var(--c-dim) !important; opacity: 0.3 !important; }
.day-lunar-special { color: #d94a43 !important; font-weight: 700 !important; opacity: 1 !important; }
.day-active {
  background: var(--c-bg) !important;
  box-shadow: inset 0 0 0 1.5px var(--c-red);
  opacity: 0.75;
  z-index: 1;
}
.day-num {
  font-size: 20px; font-family: "FZCuSong","Noto Serif SC",serif; font-weight: 600; color: var(--c-ink);
  line-height: 1.1; letter-spacing: 1px;
}
.day-lunar {
  font-size: 11px; color: var(--c-dim); text-align: center;
  font-family: "Noto Serif SC","Songti SC","SimSun",serif; font-weight: 500;
  line-height: 1.2; letter-spacing: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 100%;
}
.day-dot {
  position: absolute; top: 6px; right: 6px;
  width: 5px; height: 5px; border-radius: 50%; background: var(--c-red);
}

.cal-nav {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; border-top: 1px solid var(--c-bdr);
}
.cal-nav-label { font-size: 15px; color: var(--c-dim); letter-spacing: 1px; font-weight: 400; }
.cal-nav-label b { font-weight: 800; color: var(--c-ink); margin: 0 1px; }
.month-prev, .month-next {
  background: none; border: none; cursor: pointer; color: var(--c-dim);
  padding: 6px 8px; border-radius: 4px; transition: color 0.2s; display: flex; align-items: center;
}
.month-prev:hover, .month-next:hover { color: var(--c-red); }


/* ===== DETAIL PANEL (1:1 replica of 1.html newspaper style) ===== */
@keyframes dp-fade { from{opacity:0} to{opacity:1} }
@keyframes dp-up { from{transform:translateY(100%);opacity:0} to{transform:translateY(0);opacity:1} }
.dp {
  background: #f0f0ed; width: 100%; height: 100%; max-width: 36rem; position: relative;
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); overflow: hidden;
  display: flex; flex-direction: column; z-index: 1; animation: dp-up 0.5s cubic-bezier(0.19,1,0.22,1) forwards;
  font-family: "Noto Serif SC","Songti SC",serif; color: #2b2b2b;
  background-image: linear-gradient(to right,rgba(0,0,0,0.03) 1px,transparent 1px),linear-gradient(to bottom,rgba(0,0,0,0.03) 1px,transparent 1px);
  background-size: 20px 20px;
}
@media(min-width:640px) { .dp { height: auto; max-height: 90vh; border-radius: 0.5rem; } }
.dp-top {
  height: 36px; border-bottom: 1px solid #d6d3d1; display: flex; align-items: center;
  justify-content: space-between; padding: 0 14px; background: #fcfcfb; flex-shrink: 0;
}
.dp-top-t { font-family: "Cinzel","Times New Roman",serif; font-size: 12px; letter-spacing: 0.2em; color: #a8a29e; text-transform: uppercase }
.dp-close { background: none; border: none; color: #2b2b2b; cursor: pointer; padding: 0; line-height: 1; transition: color 0.2s }
.dp-close:hover { color: #a93226 }
.dp-scroll {
  flex: 1; overflow-y: auto; -ms-overflow-style: none; scrollbar-width: none; padding-bottom: 0;
}
.dp-scroll::-webkit-scrollbar { display: none }
.dp-date {
  padding: 12px 16px 10px; display: flex; justify-content: space-between; align-items: flex-start;
  border-bottom: 1px dashed #d6d3d1;
}
.dp-date-l { flex: 1; min-width: 0 }
.dp-term {
  display: inline-block; padding: 2px 8px; background: #292524; color: #fafaf9;
  font-size: 11px; font-weight: 700; letter-spacing: 0.1em; margin-bottom: 4px;
}
.dp-lunar {
  font-size: 1.625rem; font-weight: 700; color: #1c1917; margin-bottom: 2px; line-height: 1.2;
  font-family: "Noto Serif SC","Songti SC",serif;
}
.dp-meta { font-size: 0.875rem; color: #78716c; display: flex; align-items: center; gap: 10px }
.dp-meta-sep { width: 1px; height: 12px; background: #d6d3d1 }
.dp-date-r {
  width: 52px; height: 52px; border: 2px solid #a93226; border-radius: 0.375rem;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #a93226; background: rgba(239,68,68,0.03); flex-shrink: 0; margin-left: 12px;
}
.dp-date-mon { font-family: "Cinzel","Times New Roman",serif; font-size: 0.6875rem; font-weight: 700; text-transform: uppercase; margin-bottom: -2px }
.dp-date-day { font-size: 1.5rem; font-weight: 700; font-family: "Noto Serif SC",serif; line-height: 1 }
.dp-bazi {
  display: grid; grid-template-columns: repeat(4,1fr); border-bottom: 1px solid #d6d3d1; background: #fcfcfb;
}
.dp-pl {
  display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 12px 0;
  border-right: 1px solid #d6d3d1;
}
.dp-pl:last-child { border-right: none }
.dp-pl-hl { background: #f4f1ea }
.dp-pl-lb {
  font-family: "Cinzel","Times New Roman",serif; font-size: 9px; color: #a8a29e;
  letter-spacing: 0.15em; text-transform: uppercase; transform: scale(0.75); transform-origin: bottom center;
}
.dp-pl-ch { display: flex; flex-direction: column; gap: 3px; font-size: 1.5rem; font-weight: 700; line-height: 1 }
.dp-pl-d { color: #292524 }
.dp-pl-r { color: #991b1b }
.dp-pl-s { color: #57534e }
.dp-tags {
  display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 16px;
  border-bottom: 1px solid #d6d3d1; background: #fcfcfb;
}
.dp-tag-i {
  display: flex; align-items: center; gap: 4px; padding: 3px 8px;
  background: #f5f5f4; border: 1px solid #e7e5e4; border-radius: 4px; font-size: 11px;
}
.dp-tag-lb { color: #a8a29e; font-size: 10px; flex-shrink: 0 }
.dp-tag-val { color: #292524; font-weight: 600 }
.dp-tag-red { color: #991b1b }
.dp-panel {
  padding: 10px 16px; border-bottom: 1px solid #d6d3d1;
}
.dp-panel-top {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px; align-items: stretch;
}
.dp-sec-t {
  font-family: "Cinzel","Times New Roman",serif; font-size: 10px; color: #a8a29e;
  letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 6px;
}
.dp-panel-l { display: flex; flex-direction: column; align-items: center; justify-content: center }
.dp-compass-wrap { display: flex; justify-content: center; margin-bottom: 6px }
.dp-compass-ring {
  position: relative; width: 100px; height: 100px; border: 1.5px solid #a8a29e;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
}
.dp-compass-inner {
  position: absolute; inset: 5px; border: 1px dotted #c4b5a0; border-radius: 50%;
}
.dp-compass-cross-h {
  position: absolute; top: 50%; left: 8px; right: 8px; height: 0;
  border-top: 0.5px solid #d6d3d1; transform: translateY(-0.25px);
}
.dp-compass-cross-v {
  position: absolute; left: 50%; top: 8px; bottom: 8px; width: 0;
  border-left: 0.5px solid #d6d3d1; transform: translateX(-0.25px);
}
.dp-dir { position: absolute; font-size: 9px; color: #78716c; font-weight: 500 }
.dp-dir-n { top: 6px; left: 50%; transform: translateX(-50%) }
.dp-dir-s { bottom: 6px; left: 50%; transform: translateX(-50%) }
.dp-dir-w { left: 6px; top: 50%; transform: translateY(-50%) }
.dp-dir-e { right: 6px; top: 50%; transform: translateY(-50%) }
.dp-compass-center {
  display: flex; flex-direction: column; align-items: center; font-size: 10px; line-height: 1.3;
  z-index: 1; background: #f0f0ed; padding: 3px 6px; border-radius: 2px;
}
.dp-cc-r { color: #991b1b; font-weight: 700 }
.dp-cc-g { color: #57534e }
.dp-compass-meta {
  display: flex; gap: 12px; font-size: 10px; color: #78716c; justify-content: center;
}
.dp-panel-r { display: flex; flex-direction: column; align-items: center }
.dp-panel-bot { border-top: 1px solid #e7e5e4; padding-top: 10px }
.dp-shichen { padding: 10px 16px; border-bottom: 1px solid #d6d3d1 }
.dp-sec-t2 {
  font-family: "Cinzel","Times New Roman",serif; font-size: 10px; color: #a8a29e;
  letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 6px;
}
.dp-sc-grid { display: grid; grid-template-columns: repeat(6,1fr); gap: 1px; background: #d6d3d1; border: 1px solid #d6d3d1; border-radius: 4px; overflow: hidden }
.dp-sc {
  background: #fcfcfb; padding: 4px 2px; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 1px;
}
.dp-sc-cur { background: #f4f1ea; box-shadow: inset 0 0 0 1.5px #a93226 }
.dp-sc-name { font-size: 11px; color: #44403c; font-weight: 600 }
.dp-sc-val { font-size: 10px; font-weight: 700 }
.dp-sc-ji { color: #166534 }
.dp-sc-xiong { color: #991b1b }
.dp-yiji { padding: 10px 16px; border-bottom: 1px solid #d6d3d1; display: flex; flex-direction: column; gap: 8px }
.dp-yj-row { display: flex; align-items: flex-start; gap: 8px }
.dp-yj-dot {
  width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; font-family: "Noto Serif SC",serif; flex-shrink: 0; margin-top: 2px;
}
.dp-dot-g { border: 1.5px solid #166534; color: #166534 }
.dp-dot-r { border: 1.5px solid #991b1b; color: #991b1b }
.dp-yj-items { display: flex; flex-wrap: wrap; gap: 4px }
.dp-yj-tag {
  font-size: 12px; font-family: "Noto Serif SC",serif; letter-spacing: 0.04em;
  padding: 2px 8px; border-radius: 3px;
}
.dp-yi-tag { color: #166534; background: rgba(22,101,52,0.08) }
.dp-ji-tag { color: #991b1b; background: rgba(153,27,27,0.06) }
.dp-fx-grid {
  display: grid; grid-template-columns: repeat(3,1fr); gap: 1px; background: #d6d3d1;
  border: 1px solid #d6d3d1; border-radius: 4px; overflow: hidden;
}
.dp-fx-cell {
  background: #fcfcfb; padding: 5px 2px; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 1px;
}
.dp-fx-center { background: #f4f1ea }
.dp-fx-pos { font-size: 9px; color: #a8a29e }
.dp-fx-num { font-size: 1.125rem; font-weight: 700; font-family: "Noto Serif SC",serif; line-height: 1 }
.dp-fx-state { font-size: 11px; color: #78716c; text-align: center }
.dp-evil {
  padding: 10px 16px; background: #f5f5f4; border-top: 1px solid #e7e5e4; text-align: center;
}
.dp-evil-lb { font-size: 10px; color: #a8a29e; text-transform: uppercase; letter-spacing: 0.15em; display: block; margin-bottom: 4px }
.dp-evil-v { font-size: 13px; color: #78716c }
.dp-gua-row { display: flex; align-items: center; justify-content: center; gap: 10px; flex: 1 }
.dp-gua-item { display: flex; flex-direction: column; align-items: center; gap: 5px }
.dp-gua-svg { width: 52px; height: 68px; color: #44403c }
.dp-gua-name { font-size: 14px; font-weight: 700; color: #292524; font-family: "Noto Serif SC",serif }
.dp-gua-arrow { font-size: 20px; color: #a8a29e; margin-top: 6px }
.dp-gua-text { font-size: 12px; color: #44403c; font-weight: 600; text-align: center }
.dp-bottom-bar { height: 6px; width: 100%; background: #292524; display: flex; flex-shrink: 0 }
.dp-bb-r { width: 33.33%; height: 100%; background: #7f1d1d }
.dp-bb-g { width: 33.33%; height: 100%; background: #d6d3d1 }
.dp-bb-d { width: 33.34%; height: 100%; background: #292524 }

/* ===== PRO ALMANAC ===== */
.pro-wrap { display: flex; flex-direction: column; background: var(--p-bg); }
.pro-bar {
  background: var(--p-bar); color: var(--p-bar-text); padding: 8px 16px;
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 3px solid var(--p-red);
}
.pro-bar-l { font-size: 13px; font-weight: 500; font-family: serif; letter-spacing: 2px; }
.pro-bar-date { font-weight: 800; }
.pro-bar-r { font-size: 13px; font-weight: 500; letter-spacing: 1px; color: var(--p-bar-text); opacity: 0.85; }
.pro-bar-sep { color: var(--p-mute); opacity: 0.4; margin: 0 2px; }
.pro-bar-wk { background: rgba(255,255,255,0.1); padding: 0 4px; border-radius: 2px; font-family: monospace; margin-left: 5px; }
.pro-main {
  display: flex; gap: 20px; padding: 12px 16px; position: relative;
}
.pro-left { width: 35%; flex-shrink: 0; display: flex; flex-direction: column; padding-top: 4px; min-width: 0; overflow: hidden; }
.pro-lunar {
  font-size: 24px; font-weight: 700; font-family: serif;
  color: var(--p-ink); line-height: 1.2; letter-spacing: 1px;
}
.pro-season { font-size: 13px; font-weight: 700; color: var(--p-grn); margin-top: 6px; line-height: 1.3; letter-spacing: 1px; }
.pro-tags { display: flex; gap: 0; flex-wrap: nowrap; margin-top: 8px; flex-shrink: 0; overflow: hidden; }
.pro-tag { flex: 1; text-align: center; font-size: 9px; font-weight: 700; padding: 1px 4px; letter-spacing: 0; white-space: nowrap; border-right: 1px solid var(--p-border2); }
.pro-tag:last-child { border-right: none; }
.pro-tag-red { color: var(--p-red); }
.pro-tag-gold { color: var(--p-gold); }
.pro-tag-grn { color: var(--p-grn); }
.pro-tag-blue { color: var(--p-blue); }
.pro-tag-purple { color: var(--p-purple); }
.pro-grade {
  margin-top: 10px; font-size: 13px; color: var(--p-ink); line-height: 1.5; letter-spacing: 1px;
  font-style: italic; border-left: 3px solid var(--p-red); padding-left: 8px; padding-right: 4px;
}
.pro-grade-body { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }
.pro-grade-t { display: block; font-size: 14px; font-weight: 700; color: var(--p-ink); font-family: serif; font-style: normal; margin-bottom: 4px; letter-spacing: 1px; }
.pro-grade.pro-grade-grn { border-left-color: var(--p-grn); }
.pro-right {
  width: 65%; padding-left: 16px; border-left: 1px solid var(--p-border2);
  display: flex; flex-direction: column; justify-content: space-between;
}
.pro-term-row { display: flex; align-items: center; margin-bottom: 12px; }
.pro-pillars {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; padding: 8px;
  background: var(--p-surface); border: 1px solid var(--p-border); border-radius: 6px; flex: 1;
}
.pro-pill {
  display: flex; flex-direction: column; align-items: center;
  background: var(--p-surface2); border: 1px solid var(--p-border); border-radius: 4px;
  overflow: hidden; flex: 1;
}
.pro-pill-hd {
  background: var(--p-border); color: var(--p-mute2); font-size: 10px;
  width: 100%; text-align: center; padding: 3px 0; font-weight: 700; letter-spacing: 3px;
}
.pro-pill-bd {
  padding: 10px 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
  font-family: serif; font-weight: 700; font-size: 24px; color: var(--p-ink); letter-spacing: 1px; flex: 1;
}
.pro-pill-ny {
  font-size: 10px; color: var(--p-red); font-weight: 600; padding: 2px 4px 6px; letter-spacing: 1px;
  text-align: center; line-height: 1.2; margin-top: auto;
}
.pro-deities {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
  padding: 0 16px 12px; border-top: 1px dashed var(--p-border2); margin-top: 0; padding-top: 12px;
}
.pro-deity {
  background: var(--p-surface); border: 1px solid var(--p-border); border-radius: 4px; padding: 6px;
  display: flex; justify-content: center; align-items: center; gap: 6px;
  font-size: 13px; font-family: serif; text-align: center; letter-spacing: 1px;
}
.pro-deity-l { font-weight: 700; color: var(--p-dim); letter-spacing: 1px; }
.pro-deity-v { font-weight: 600; color: var(--p-ink); letter-spacing: 1px; }
.pro-micro { padding: 0 16px 20px; }
.pro-micro-grid {
  background: var(--p-surface); border: 1px solid var(--p-border); border-radius: 4px; padding: 8px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; font-size: 12px; color: var(--p-dim); letter-spacing: 1px;
}
.pro-mi { display: flex; justify-content: space-between; border-bottom: 1px solid var(--p-border); padding-bottom: 4px; }
.pro-mi-l { color: var(--p-dim); }
.pro-mi-v { font-weight: 600; }
.pro-mi-red { color: var(--p-red); }
.pro-gods { font-size: 14px; line-height: 1.6; color: var(--p-dim2); padding: 0 16px 16px; }
.pro-god-row { margin-bottom: 1px; }
.pro-god-l { font-weight: 700; margin-right: 4px; }
.pro-god-good { color: var(--p-grn); }
.pro-god-bad { color: var(--p-red); }
.pro-god-v { color: var(--p-dim); }

/* ===== K-LINE ALMANAC ===== */
.k-wrap { display:flex;flex-direction:column;background:var(--k-bg);color:var(--k-ink);font-family:"SF Mono",Menlo,"Courier New",monospace;position:relative;overflow:hidden }
.k-wrap::before { content:'';position:absolute;top:-30%;left:10%;width:400px;height:400px;background:radial-gradient(circle,var(--k-glow) 0%,transparent 70%);pointer-events:none }
.k-ticker { --tk-w:1000px;height:24px;border-bottom:1px solid var(--k-bdr);background:var(--k-ticker-bg);overflow:hidden;position:relative;z-index:1;user-select:none;display:flex }
.k-ticker-a,.k-ticker-b { display:flex;flex-shrink:0;align-items:center;white-space:nowrap;font-size:11px;color:var(--k-dim);letter-spacing:0.5px;line-height:24px;will-change:transform;animation:k-marquee 30s linear infinite }
.k-ticker-a span,.k-ticker-b span { padding:0 12px;flex-shrink:0 }
.k-tk-warn { color:var(--k-line-xiong,#f43f5e) }
.k-tk-ok { color:var(--k-line-ji,#22c55e) }
@keyframes k-marquee { 0%{transform:translateX(0)} 100%{transform:translateX(calc(var(--tk-w) * -1))} }
.k-head { padding:10px 14px 6px;display:flex;justify-content:space-between;align-items:flex-end;position:relative;z-index:1 }
.k-head-l { flex:1 }
.k-time { font-size:36px;font-weight:700;letter-spacing:-2px;line-height:1;background:linear-gradient(180deg,var(--k-time-grad-start) 0%,var(--k-time-grad-end) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text }
.k-status { display:flex;align-items:center;gap:6px;margin-top:4px }
.k-dot { width:6px;height:6px;border-radius:50%;animation:k-pulse 2s ease-in-out infinite }
.k-dot-g { background:var(--k-line-ji,#22c55e) }
.k-dot-r { background:var(--k-line-xiong,#f43f5e) }
@keyframes k-pulse { 0%,100%{opacity:0.4} 50%{opacity:1} }
.k-status-t { font-size:12px;font-weight:700;color:var(--k-accent,#c4b5fd);letter-spacing:1px }
.k-status-sub { font-size:10px;color:var(--k-dim);margin-left:4px }
.k-head-r { text-align:center }
.k-score { font-size:28px;font-weight:700;font-family:"SF Mono",Menlo,monospace;line-height:1;color:var(--k-ink) }
.k-score-label { font-size:9px;font-weight:600;color:var(--k-dim);letter-spacing:2px;margin-top:3px }
.k-body { padding:6px 14px;position:relative;z-index:1 }
.k-chart-hd { display:flex;justify-content:space-between;align-items:center;margin-bottom:6px }
.k-chart-title { font-size:11px;font-weight:700;color:var(--k-dim);letter-spacing:2px }
.k-chart-ratio { font-size:11px;font-weight:700;color:var(--k-dim) }
.k-ratio-ji { color:var(--k-line-ji,#22c55e) }
.k-ratio-xiong { color:var(--k-line-xiong,#f43f5e) }
.k-chart { background:var(--k-chart-bg);border-radius:6px;border:1px solid var(--k-bdr);padding:6px 6px 0;position:relative }
.k-svg { width:100%;height:80px;display:block }
.k-dots { position:absolute;top:6px;left:6px;right:6px;height:80px;pointer-events:none }
.k-pt { position:absolute;width:4px;height:4px;border-radius:50%;transform:translate(-50%,-50%) }
.k-pt-cur { width:7px;height:7px;box-shadow:0 0 0 1.5px var(--k-bg,#0a0a0f),0 0 0 3px currentColor;z-index:2 }
.k-x-axis { position:relative;height:18px }
.k-x-label { position:absolute;transform:translateX(-50%);font-size:9px;color:var(--k-dim);font-weight:600;top:2px }
.k-x-cur { color:var(--k-accent,#c4b5fd);font-weight:700;font-size:10px }
.k-wx-bar { display:flex;justify-content:center;gap:12px;margin-top:6px;font-size:10px;color:var(--k-dim);font-weight:600 }
.k-wx-item { display:flex;align-items:center;gap:3px }
.k-wx-dot { width:6px;height:6px;border-radius:50% }
.k-pillars { display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin-top:8px }
.k-pill { background:var(--k-surface);border:1px solid var(--k-bdr);border-radius:6px;padding:6px 4px;display:flex;flex-direction:column;align-items:center;gap:1px }
.k-pill-label { font-size:10px;color:var(--k-dim) }
.k-pill-gz { font-size:16px;font-weight:700;font-family:"Noto Serif SC",serif;color:var(--k-ink) }
.k-bottom { padding:6px 14px 12px;position:relative;z-index:1 }
.k-yiji { display:grid;grid-template-columns:1fr 1fr;gap:6px }
.k-yi { background:var(--k-surface);border:1px solid var(--k-bdr);border-radius:8px;padding:8px 10px }
.k-yi-hd { display:flex;align-items:center;gap:5px;font-size:12px;font-weight:700;color:var(--k-dim);margin-bottom:4px }
.k-yi-dot { width:6px;height:6px;border-radius:50% }
.k-yi-dot-g { background:var(--k-line-ji,#22c55e) }
.k-yi-dot-r { background:var(--k-line-xiong,#f43f5e) }
.k-yi-bd { font-size:12px;line-height:1.5;font-family:-apple-system,"PingFang SC",sans-serif }
.k-yi-bd-g { color:var(--k-line-ji,#22c55e) }
.k-yi-bd-r { color:var(--k-line-xiong,#f43f5e) }
`;
  }
}

class AlmanacCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; }
  setConfig(config) { this._config = { ...config }; this._render(); }
  set hass(hass) { this._hass = hass; }
  _render() {
    const style = this._config.card_style || "classic";
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;font-family:-apple-system,"Helvetica Neue","PingFang SC",sans-serif;--e-accent:var(--primary-color,#03a9f4);--e-ink:var(--primary-text-color,#333);--e-dim:var(--secondary-text-color,#999);--e-bg:var(--card-background-color,var(--ha-card-background,#fff));--e-bg2:var(--secondary-background-color,#f5f5f5);--e-bdr:var(--divider-color,rgba(0,0,0,0.1))}
        .ed{color:var(--e-ink);padding:16px;display:flex;flex-direction:column;gap:12px}
        .ed-hd{display:flex;align-items:center;gap:10px;padding-bottom:12px;border-bottom:1px solid var(--e-bdr)}
        .ed-hd-icon{width:36px;height:36px;border-radius:10px;background:var(--e-accent);display:flex;align-items:center;justify-content:center}
        .ed-hd-icon svg{color:#fff}
        .ed-hd-txt{flex:1}
        .ed-title{font-size:15px;font-weight:700;color:var(--e-ink)}
        .ed-sub{font-size:10px;color:var(--e-dim);margin-top:2px}
        .ed-mod{border:1px solid var(--e-bdr);border-radius:10px;overflow:hidden}
        .ed-mod-hd{padding:10px 14px;font-size:13px;font-weight:600;color:var(--e-ink);cursor:pointer;display:flex;align-items:center;user-select:none)}
        .ed-mod-hd .ed-arrow{margin-left:auto;width:8px;height:8px;border-right:2px solid var(--e-dim);border-bottom:2px solid var(--e-dim);transform:rotate(-45deg);transition:transform 0.2s}
        .ed-mod-hd.open .ed-arrow{transform:rotate(45deg)}
        .ed-mod-bd{padding:12px 14px;display:none}
        .ed-mod-bd.open{display:block}
        .ed-styles{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
        .ed-sty{border:1.5px solid var(--e-bdr);border-radius:10px;padding:14px 8px;cursor:pointer;text-align:center;transition:all 0.15s;background:var(--e-bg);position:relative}
        .ed-sty:hover{border-color:var(--e-accent)}
        .ed-sty.active{border-color:var(--e-accent);background:color-mix(in srgb,var(--e-accent) 6%,transparent)}
        
        .ed-sty-icon{margin-bottom:6px;color:var(--e-dim);transition:color 0.15s}
        .ed-sty.active .ed-sty-icon{color:var(--e-accent)}
        .ed-sty-name{font-size:12px;font-weight:600;color:var(--e-ink)}
        .ed-sty-desc{font-size:10px;color:var(--e-dim);margin-top:2px}
        .fd label{display:block;font-size:11px;font-weight:500;color:var(--e-dim);margin-bottom:4px}
        .fd input[type="text"]{width:100%;padding:8px 10px;border:1px solid var(--e-bdr);border-radius:8px;font-size:12px;background:var(--e-bg);color:var(--e-ink);box-sizing:border-box;transition:border 0.15s;font-family:"SF Mono",Menlo,monospace}
        .fd input:focus{outline:none;border-color:var(--e-accent)}
      </style>
      <div class="ed">
        <div class="ed-hd">
          <div class="ed-hd-icon"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div>
          <div class="ed-hd-txt">
            <div class="ed-title">中国老黄历</div>
            <div class="ed-sub">Chinese Almanac Card · Imperial Metaphysics</div>
          </div>
        </div>
        <div class="ed-mod">
          <div class="ed-mod-hd open" data-sec="style">卡片样式<span class="ed-arrow"></span></div>
          <div class="ed-mod-bd open" data-sec="style">
            <div class="ed-styles">
              <div class="ed-sty${style==="classic"?" active":""}" data-style="classic">
                <div class="ed-sty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="4" x2="9" y2="10"/></svg></div>
                <div class="ed-sty-name">经典月历</div>
                <div class="ed-sty-desc">月历网格 · 简洁清爽</div>
              </div>
              <div class="ed-sty${style==="pro"?" active":""}" data-style="pro">
                <div class="ed-sty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="9"/><line x1="12" y1="3" x2="12" y2="21"/><line x1="3" y1="12" x2="21" y2="12"/><path d="M12 3a15.3 15.3 0 0 1 4 9 15.3 15.3 0 0 1-4 9"/></svg></div>
                <div class="ed-sty-name">专业排盘</div>
                <div class="ed-sty-desc">四柱择日 · 全维数据</div>
              </div>
              <div class="ed-sty${style==="kline"?" active":""}" data-style="kline">
                <div class="ed-sty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 4-8"/></svg></div>
                <div class="ed-sty-name">黄历K线</div>
                <div class="ed-sty-desc">五行能量 · 梦核风格</div>
              </div>
            </div>
          </div>
        </div>
        <div class="ed-mod">
          <div class="ed-mod-hd" data-sec="basic">基础设置<span class="ed-arrow"></span></div>
          <div class="ed-mod-bd" data-sec="basic">
            <div class="fd"><label>传感器前缀</label><input type="text" id="prefix" value="${this._config.prefix||"zhong_guo_lao_huang_li_"}"/></div>
          </div>
        </div>
      </div>`;
    this.shadowRoot.querySelectorAll(".ed-mod-hd").forEach(hd=>{hd.addEventListener("click",()=>{const bd=hd.nextElementSibling;const isOpen=hd.classList.contains("open");hd.classList.toggle("open");bd.classList.toggle("open")})});
    this.shadowRoot.querySelectorAll(".ed-sty").forEach(el=>{el.addEventListener("click",()=>{this._config={...this._config,card_style:el.dataset.style};this._fire();this._render()})});
    this.shadowRoot.getElementById("prefix").addEventListener("change",e=>{this._config={...this._config,prefix:e.target.value};this._fire()});
  }
  _fire(){this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:true,composed:true}))}
}

customElements.define("almanac-card-editor", AlmanacCardEditor);
customElements.define("almanac-card", AlmanacCard);
