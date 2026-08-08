const documents = [
  {
    id: "KG-APT-001", short: "言语 · 35", title: "言语理解", subtitle: "片段 15 + 填空 10", state: "限时中", folder: "行测 / 言语理解与表达", priority: "中",
    date: "2026-08-01 19:30", status: "正确率 78%", description: "片段阅读 15 题目标 12 分钟，逻辑填空 10 题目标 8 分钟；错因集中在成语色彩、转折后主旨和选项偷换概念。", tags: ["片段阅读", "逻辑填空", "20 分钟"],
    advice: ["复盘只记录主旨偏移、语境误判、成语色彩三类错因", "二刷同型题时把选项偷换概念单独标红"], accent: "silver", completion: 78,
  },
  {
    id: "KG-APT-002", short: "判断 · 40", title: "判断推理", detailTitle: "图推定义类比混合组", subtitle: "图推 8 + 定义 6 + 类比 6", state: "提速", folder: "行测 / 判断推理", priority: "中",
    date: "2026-08-01 20:00", status: "正确率 82%", description: "图形推理 8 题目标 6 分钟，定义判断 6 题目标 5 分钟，类比 6 题目标 4 分钟；主要错因是规则迁移和必要条件误判。", tags: ["图形推理", "定义判断", "规则迁移"],
    advice: ["图推先扫位置、样式、数量、属性四类规律", "定义判断逐字锁定必要条件，避免被题干例子牵引"], accent: "mist", completion: 82,
  },
  {
    id: "KG-APT-003", short: "数量 · 12", title: "数量关系", subtitle: "工程/利润/行程", state: "保 8 争 10", folder: "行测 / 数量关系", priority: "高",
    date: "2026-08-01 20:15", status: "正确率 61%", description: "工程、利润、行程各 4 题，15 分钟内先保 8 题；错因按建模错误、方程设元、尾数计算分别复盘。", tags: ["工程问题", "利润问题", "行程问题"],
    advice: ["先做能在 70 秒内建模的题，难题标记后置", "把放弃题记录为题型识别失败或计算成本过高"], accent: "green", completion: 61,
  },
  {
    id: "KG-APT-004", short: "资料 · 20", title: "资料分析", subtitle: "4 篇 20 题", state: "高优先级", folder: "行测 / 资料分析", priority: "高",
    date: "2026-08-01 20:30", status: "正确率 74%", description: "4 篇 20 题控制在 28 分钟内，增长率、比重、平均数是高频失分点；每篇记录列式、估算口径和跳题点。", tags: ["增长率", "比重", "平均数"],
    advice: ["先做增长率与比重混合 12 题，记录列式犹豫点", "套卷复盘只保留可迁移的速算口径和错因标签"], accent: "ice", completion: 74,
  },
  {
    id: "KG-APT-005", short: "常识 · 20", title: "常识判断", subtitle: "法律/科技/党政文件", state: "滚动积累", folder: "行测 / 常识判断", priority: "中",
    date: "2026-08-01 21:00", status: "正确率 58%", description: "法律、科技、党政文件各 5 题滚动复习；错因按知识盲区、时政迁移失败、概念混淆归类。", tags: ["法律常识", "科技常识", "党政文件"],
    advice: ["常识不做长时间硬耗，错题只沉淀可迁移知识点", "把本周时政转化为常识判断背景材料"], accent: "warm", completion: 58,
  },
  {
    id: "KG-SL-006", short: "申论 · 小题", title: "申论小题", subtitle: "概括/分析/对策/贯彻", state: "精修", folder: "申论 / 小题采分", priority: "高",
    date: "2026-08-02 09:30", status: "64/100", description: "归纳概括控制 200 字内 8 个采分点，综合分析先解释再评价，提出对策必须含主体、动作、资源和验收标准。", tags: ["归纳概括", "综合分析", "贯彻执行"],
    advice: ["每道小题先列材料段落关键词，再压缩成采分点", "贯彻执行题单独检查格式、对象、语气和落款"], accent: "ice", completion: 68,
  },
  {
    id: "KG-PAPER-007", short: "套卷 · 3", title: "真题套卷", subtitle: "2024-2026 国考", state: "复盘中", folder: "真题 / 国考套卷", priority: "高",
    date: "2026-08-03 09:00", status: "差进面线 4.5", description: "2026 地市级、2025 副省级、2024 行政执法三套卷复盘；记录行测分模块耗时、申论小题采分点和大作文立意偏差。", tags: ["全真 120 分钟", "套卷复盘", "进面线"],
    advice: ["复盘表必须包含题号、题型、目标用时、实际用时、错因和二刷日期", "申论第二题格式扣分要单列模板重写"], accent: "silver", completion: 61,
  },
  {
    id: "KG-REVIEW-008", short: "错题 · 46", title: "错题复盘", subtitle: "四类错因归档", state: "待二刷", folder: "复盘 / 错题本", priority: "中",
    date: "2026-08-03 21:30", status: "46 题待二刷", description: "错题按审题偏差、知识缺口、列式错误、时间失控归因；二刷只看同型迁移是否稳定，而不是重复记答案。", tags: ["错因归因", "二刷", "同型迁移"],
    advice: ["每晚只处理当天错题，超过 48 小时会失真", "同型题连续 3 次正确后再移出高频错因列表"], accent: "mist", completion: 89,
  },
  {
    id: "KG-JOB-009", short: "岗位 · 3", title: "岗位雷达", subtitle: "税务/海关/调查队", state: "筛选中", folder: "选岗 / 职位表", priority: "高",
    date: "2026-10-15 09:00", status: "预估报考比 68-186:1", description: "岗位字段同步核对招录数、报考比、进面线、学历、专业、政治面貌、基层年限、最低服务期和体检限制。", tags: ["招录数", "报考比", "进面线"],
    advice: ["税务系统综合管理招录 3 人、报考比 186:1、进面线 132.4，建议安全线 137", "海关监管一线需提前确认体检和现场执法适配"], accent: "warm", completion: 42,
  },
];

const groups = [
  { name: "行测限时", count: 5, color: "var(--accent-400)", items: [["言语 25 题：片段 15 + 逻辑填空 10", "20 分钟", "正确率目标 80%"], ["判断 20 题：图推/定义/类比", "18 分钟", "错因：规则迁移"], ["资料 4 篇 20 题", "28 分钟", "错因：列式犹豫"]] },
  { name: "申论闭环", count: 4, color: "#56b8ff", items: [["归纳概括：200 字 8 个采分点", "精修", "主体遗漏"], ["提出对策：主体-动作-资源-验收", "重写", "可操作性不足"]] },
  { name: "岗位与节点", count: 5, color: "#9c82ff", items: [["国考公告与职位表", "2026.10", "专业/学历/政治面貌"], ["报名缴费与准考证", "2026.11", "省考联考同步关注"], ["资格复审材料", "2026.12", "面试素材库"]] },
];

const materialPalettes = {
  cyan: ["#27e8df", "#11a9c8", "#17346f"],
  original: ["#ff4aa9", "#ff8849", "#aa49ff"],
  rain: ["#2e66ff", "#ff693f", "#4721ac"],
  chrome: ["#f4f8f6", "#8d9996", "#11172b"],
};

let selectedIndex = 3;
let isPlaying = true;
let speed = 2;
let autoplayTimer;
let autoplayLastFrame = 0;
let pointerStart = null;
let pointerCurrent = null;
let toastTimer;
let detailAnimationTimer;
let motionTimer;
let visualPosition = selectedIndex;
let targetPosition = selectedIndex;
let carouselFrame = null;
let lastFrameTime = 0;
let lastWheelDirection = 1;
let dragOriginPosition = selectedIndex;
let viewMode = "orbit";
let selectedMetricIndex = 0;
let themePreference = document.documentElement.dataset.theme || "dark";
let accentPreference = document.documentElement.dataset.accent || "ocean";

const scene = document.querySelector("#cardScene");
const viewport = document.querySelector("#carouselViewport");
const playToggle = document.querySelector("#playToggle");
const playLabel = playToggle.querySelector(".play-label");
const orbitModeBtn = document.querySelector("#orbitModeBtn");
const fanModeBtn = document.querySelector("#fanModeBtn");
const timelineDates = document.querySelector("#timelineDates");
const progress = document.querySelector("#timelineProgress");
const detailsContent = document.querySelector(".details-content");
const materialOverlay = document.querySelector("#materialOverlay");
const materialPreview = document.querySelector("#materialPreview");
const metricCards = [...document.querySelectorAll(".metric-card")];
const materialCardSelect = document.querySelector("#materialCardSelect");
const themeControl = document.querySelector(".theme-control");
const themeToggleBtn = document.querySelector("#themeToggleBtn");
const systemThemeQuery = window.matchMedia("(prefers-color-scheme: light)");
metricCards.forEach((card) => {
  const opacity = Number(card.dataset.opacity || 100) / 100;
  const blur = Number(card.dataset.blur || 18);
  const flow = Number(card.dataset.flow || 200);
  card.style.setProperty("--material-opacity", opacity);
  card.style.setProperty("--material-blur", `${blur}px`);
  card.style.setProperty("--flow-duration", `${Math.max(2.2, 8 - flow / 50)}s`);
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-pressed", "false");
  card.setAttribute("aria-label", `选择${card.querySelector("h3").textContent}进行配色设置`);
  const marker = document.createElement("span");
  marker.className = "metric-select-mark";
  marker.setAttribute("aria-hidden", "true");
  marker.textContent = "✓ 已选择";
  card.appendChild(marker);
});
const initialMetricStates = metricCards.map((card) => ({
  material: card.dataset.material || "original",
  opacity: card.dataset.opacity || "100",
  blur: card.dataset.blur || "18",
  flow: card.dataset.flow || "200",
  colors: [card.dataset.colorA || "#f4f8f6", card.dataset.colorB || "#8d9996", card.dataset.colorC || "#11172b"],
}));

function icon(name) {
  return `<svg aria-hidden="true"><use href="#${name}"/></svg>`;
}

function renderQueue() {
  const container = document.querySelector("#queueGroups");
  container.innerHTML = groups.map((group, groupIndex) => `
    <article class="queue-group ${groupIndex === 0 ? "open" : ""}">
      <button class="group-head" style="--group-color:${group.color}"><span><i></i>${group.name} <b>${group.count}</b></span><svg><use href="#i-chevron"/></svg></button>
      <div class="group-items">
        ${group.items.map((item) => `<button class="queue-item"><span>${item[0]}</span><em class="${item[1] === "在读" ? "reading" : ""}">${item[1]}</em><small>${item[2]}</small></button>`).join("")}
      </div>
    </article>
  `).join("");

  container.querySelectorAll(".group-head").forEach((button) => {
    button.addEventListener("click", () => button.closest(".queue-group").classList.toggle("open"));
  });
  container.querySelectorAll(".queue-item").forEach((button) => button.addEventListener("click", () => showToast(`已打开「${button.querySelector("span").textContent}」`)));
}

function renderCards() {
  scene.innerHTML = documents.map((doc, index) => `
    <button class="doc-card ${doc.accent} tone-${doc.tone || "green"}" data-index="${index}" aria-label="打开${doc.title}">
      <span class="paper-shine"></span>
      <span class="doc-kicker">${doc.short}</span>
      <span class="doc-lines"><i></i><i></i><i></i><i></i><i></i></span>
      <span class="doc-symbol">${index === 8 ? "岗" : index === 6 ? "卷" : index === 5 ? "申" : index === 3 ? "资" : "题"}</span>
      <span class="doc-copy"><strong>${doc.title}</strong><small>${doc.subtitle} · ${doc.state}</small></span>
    </button>
  `).join("");
  scene.querySelectorAll(".doc-card").forEach((card) => card.addEventListener("click", () => selectCard(Number(card.dataset.index), true)));
}

function renderTimeline() {
  const days = ["01", "08", "15", "22", "29", "05", "12", "19", "26", "03", "10", "17", "24", "31", "07", "14", "21", "28", "04", "11", "18", "25", "27", "29"];
  timelineDates.innerHTML = days.map((day, index) => {
    const marker = index === 10 ? "岗" : index === 23 ? "考" : "";
    return `<button data-day-index="${index}" class="${index === 10 ? "active" : ""}">${marker ? `<i>${marker}</i>` : ""}${day}</button>`;
  }).join("");
  timelineDates.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
    timelineDates.querySelector(".active")?.classList.remove("active");
    button.classList.add("active");
    selectCard(Number(button.dataset.dayIndex) % documents.length);
  }));
}

function modulo(value, length = documents.length) {
  return ((value % length) + length) % length;
}

function relativePosition(index, position = visualPosition) {
  let delta = index - modulo(position);
  const half = documents.length / 2;
  if (delta > half) delta -= documents.length;
  if (delta < -half) delta += documents.length;
  return delta;
}

function updateCardPositions(position = visualPosition) {
  scene.querySelectorAll(".doc-card").forEach((card) => {
    const cardIndex = Number(card.dataset.index);
    const delta = relativePosition(cardIndex, position);
    const absolute = Math.abs(delta);
    const fanView = viewMode === "fan";
    const x = fanView ? -12 + delta * 46 : 85 + Math.sin(delta * .6) * 270;
    const z = fanView ? (absolute < .08 ? 105 : 58 - Math.min(absolute, 4.5) * 7) : 80 - Math.min(absolute, 2.5) * 70;
    const y = fanView ? 2 + Math.min(absolute, 4.5) * 2.5 : Math.min(absolute, 2.5) * 7;
    const rotation = fanView
      ? (absolute < .08 ? -34 : -Math.min(64, 56 + absolute * 1.8))
      : -Math.sign(delta) * Math.min(22, absolute * 11);
    const scale = fanView ? (absolute < .08 ? 1.02 : Math.max(.88, .98 - absolute * .018)) : Math.max(.72, 1.02 - absolute * .12);
    card.style.setProperty("--x", `${x}px`);
    card.style.setProperty("--y", `${y}px`);
    card.style.setProperty("--z", `${z}px`);
    card.style.setProperty("--rotate", `${rotation}deg`);
    card.style.setProperty("--scale", scale);
    const depthOpacity = fanView ? Math.max(.52, 1 - absolute * .105) : Math.max(.46, 1 - absolute * .22);
    const wrapFade = fanView ? (absolute > 3.8 ? Math.max(.46, 1 - (absolute - 3.8) * .7) : 1) : (absolute > 2.15 ? Math.max(0, (2.5 - absolute) / .35) : 1);
    const cardOpacity = depthOpacity * wrapFade;
    card.style.setProperty("--opacity", cardOpacity);
    card.style.setProperty("--card-delay", "0ms");
    card.style.zIndex = String(fanView && absolute < .08 ? 90 : Math.round(fanView ? 58 + delta * 2 : 30 - absolute * 8));
    card.style.pointerEvents = cardOpacity < .08 ? "none" : "auto";
    card.tabIndex = cardOpacity < .08 ? -1 : 0;
    card.classList.toggle("selected", cardIndex === selectedIndex);
    card.setAttribute("aria-current", cardIndex === selectedIndex ? "true" : "false");
  });
}

function setViewMode(mode) {
  viewMode = mode === "fan" ? "fan" : "orbit";
  const fanView = viewMode === "fan";
  viewport.classList.toggle("fan-view", fanView);
  viewport.classList.add("view-switching");
  orbitModeBtn.classList.toggle("active", !fanView);
  orbitModeBtn.classList.toggle("quiet", fanView);
  orbitModeBtn.setAttribute("aria-pressed", String(!fanView));
  fanModeBtn.classList.toggle("active", fanView);
  fanModeBtn.classList.toggle("quiet", !fanView);
  fanModeBtn.setAttribute("aria-pressed", String(fanView));
  viewport.setAttribute("aria-label", fanView ? "可滚轮切换的侧向层叠备考卡片" : "可滚轮切换的备考模块卡片");
  document.querySelector(".scroll-tip p").textContent = fanView ? "连续滚动浏览侧向层叠；点击卡片展开" : "连续滚动转动模块环；点击卡片展开";
  updateCardPositions(visualPosition);
  window.setTimeout(() => viewport.classList.remove("view-switching"), 760);
}

function startCarouselAnimation() {
  if (carouselFrame !== null) return;
  viewport.classList.add("continuous-motion");
  lastFrameTime = performance.now();

  const tick = (now) => {
    const elapsed = Math.min(32, now - lastFrameTime);
    lastFrameTime = now;
    const distance = targetPosition - visualPosition;
    const smoothing = 1 - Math.exp(-elapsed / 170);
    visualPosition += distance * smoothing;
    const visualIndex = modulo(Math.round(visualPosition));
    if (visualIndex !== selectedIndex) {
      selectedIndex = visualIndex;
      const direction = Math.sign(targetPosition - visualPosition) || lastWheelDirection;
      if (direction) kickScene(direction);
      updateDetails(documents[selectedIndex]);
    }
    updateCardPositions(visualPosition);

    if (Math.abs(distance) < .006) {
      visualPosition = targetPosition;
      updateCardPositions(visualPosition);
      carouselFrame = null;
      viewport.classList.remove("continuous-motion");
      return;
    }
    carouselFrame = requestAnimationFrame(tick);
  };

  carouselFrame = requestAnimationFrame(tick);
}

function kickScene(direction) {
  const motionClass = direction < 0 ? "moving-backward" : "moving-forward";
  viewport.classList.remove("moving-forward", "moving-backward");
  void viewport.offsetWidth;
  viewport.classList.add(motionClass);
  window.clearTimeout(motionTimer);
  motionTimer = window.setTimeout(() => viewport.classList.remove(motionClass), 880);
}

function updateDetails(doc) {
  document.querySelector("#detailId").textContent = doc.id;
  document.querySelector("#detailTitle").textContent = doc.detailTitle || doc.title;
  document.querySelector("#detailStatus").textContent = doc.status;
  document.querySelector("#detailDescription").textContent = doc.description;
  document.querySelector("#detailFolder").textContent = doc.folder;
  document.querySelector("#detailDate").textContent = doc.date;
  document.querySelector("#detailState").textContent = doc.state;
  document.querySelector("#detailPriority").textContent = doc.priority;
  document.querySelector("#detailTags").innerHTML = doc.tags.map((tag) => `<span>${tag}</span>`).join("");
  document.querySelector("#detailAdvice").innerHTML = doc.advice.map((line) => `<li>${line}</li>`).join("");
  document.querySelector("#completionValue").textContent = `${doc.completion}%`;
  document.querySelector(".completion-card b").style.width = `${doc.completion}%`;
  document.querySelector("#tipTitle").textContent = doc.title;
  progress.style.width = `${25 + selectedIndex * (56 / Math.max(1, documents.length - 1))}%`;
  detailsContent.classList.remove("detail-refresh");
  void detailsContent.offsetWidth;
  detailsContent.classList.add("detail-refresh");
  window.clearTimeout(detailAnimationTimer);
  detailAnimationTimer = window.setTimeout(() => detailsContent.classList.remove("detail-refresh"), 620);
}

function commitCarouselTarget(position, explicit = false, requestedDirection = 0) {
  targetPosition = position;
  lastWheelDirection = requestedDirection || Math.sign(targetPosition - visualPosition) || lastWheelDirection;
  startCarouselAnimation();
  if (explicit && isPlaying) restartAutoplay();
}

function selectCard(index, explicit = false, requestedDirection = 0) {
  const normalizedIndex = modulo(index);
  const delta = requestedDirection || relativePosition(normalizedIndex, visualPosition);
  if (Math.abs(delta) < .001) {
    selectedIndex = normalizedIndex;
    visualPosition = normalizedIndex;
    targetPosition = normalizedIndex;
    updateCardPositions(visualPosition);
    updateDetails(documents[selectedIndex]);
    return;
  }
  commitCarouselTarget(visualPosition + delta, explicit, Math.sign(delta));
}

function nextCard(direction = 1) {
  commitCarouselTarget(Math.round(targetPosition) + direction, false, direction);
}

function restartAutoplay() {
  if (autoplayTimer) cancelAnimationFrame(autoplayTimer);
  autoplayTimer = null;
  if (!isPlaying || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  autoplayLastFrame = performance.now();
  const advance = (now) => {
    const elapsed = Math.min(34, now - autoplayLastFrame);
    autoplayLastFrame = now;
    targetPosition -= elapsed * .00018 * speed;
    lastWheelDirection = -1;
    startCarouselAnimation();
    autoplayTimer = requestAnimationFrame(advance);
  };
  autoplayTimer = requestAnimationFrame(advance);
}

function setPlaying(value) {
  isPlaying = value;
  playToggle.classList.toggle("playing", value);
  playToggle.classList.toggle("active", value);
  playLabel.textContent = value ? "自动播放中" : "自动播放";
  restartAutoplay();
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 1800);
}

function resolveTheme(preference = themePreference) {
  return preference === "system" ? (systemThemeQuery.matches ? "light" : "dark") : preference;
}

function applyTheme(preference, { persist = true, announce = false } = {}) {
  themePreference = ["system", "light", "dark"].includes(preference) ? preference : "dark";
  const resolvedTheme = resolveTheme();
  const labels = { system: "跟随系统", light: "亮色", dark: "暗色" };
  const icons = { system: "◐", light: "☀", dark: "☾" };
  const themeOrder = ["system", "light", "dark"];
  const nextTheme = themeOrder[(themeOrder.indexOf(themePreference) + 1) % themeOrder.length];
  document.documentElement.dataset.theme = themePreference;
  document.documentElement.dataset.themeResolved = resolvedTheme;
  document.documentElement.style.colorScheme = resolvedTheme;
  document.querySelector('meta[name="theme-color"]').content = resolvedTheme === "light" ? "#eef3f0" : "#080b0a";
  themeToggleBtn.querySelector(".theme-toggle-icon").textContent = icons[themePreference];
  const resolvedHint = themePreference === "system" ? `（当前${labels[resolvedTheme]}）` : "";
  themeToggleBtn.setAttribute("aria-label", `切换显示主题，当前${labels[themePreference]}${resolvedHint}`);
  themeToggleBtn.title = `${labels[themePreference]}${resolvedHint} · 点击切换为${labels[nextTheme]}`;
  if (persist) {
    try { localStorage.setItem("kaogong-workbench-theme", themePreference); } catch {}
  }
  if (announce) showToast(`已切换为${labels[themePreference]}${resolvedHint}`);
}

function applyAccent(accent, { persist = true, announce = false } = {}) {
  const accentNames = { emerald: "翡翠", ocean: "静海", iris: "鸢尾", amber: "琥珀", sakura: "绯樱" };
  accentPreference = Object.hasOwn(accentNames, accent) ? accent : "ocean";
  document.documentElement.dataset.accent = accentPreference;
  document.querySelectorAll("[data-accent-option]").forEach((button) => {
    const selected = button.dataset.accentOption === accentPreference;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  document.querySelector("#accentName").textContent = accentNames[accentPreference];
  if (persist) {
    try { localStorage.setItem("kaogong-workbench-accent", accentPreference); } catch {}
  }
  if (announce) showToast(`界面强调色已切换为「${accentNames[accentPreference]}」`);
}

function currentMetricCard() {
  return metricCards[selectedMetricIndex];
}

function selectMetricCard(index, { announce = false, syncDrawer = true } = {}) {
  selectedMetricIndex = Math.max(0, Math.min(metricCards.length - 1, Number(index) || 0));
  materialCardSelect.value = String(selectedMetricIndex);
  metricCards.forEach((card, cardIndex) => {
    const selected = cardIndex === selectedMetricIndex;
    card.classList.toggle("selected", selected);
    card.setAttribute("aria-pressed", String(selected));
  });
  const selectedCard = currentMetricCard();
  selectedCard.classList.remove("selection-kick");
  void selectedCard.offsetWidth;
  selectedCard.classList.add("selection-kick");
  window.setTimeout(() => selectedCard.classList.remove("selection-kick"), 560);
  const cardName = selectedCard.querySelector("h3").textContent;
  document.querySelector("#materialSettingsBtn").setAttribute("aria-label", `设置${cardName}的流体配色`);
  document.querySelector("#materialSettingsBtn").title = `设置「${cardName}」配色`;
  if (syncDrawer && materialOverlay.classList.contains("open")) syncMaterialDrawer();
  if (announce) showToast(`已选择「${cardName}」· 点击顶部调节按钮设置配色`);
}

function replayMaterialMorph() {
  [materialPreview, currentMetricCard()].forEach((element) => {
    element.classList.remove("material-morph");
    void element.offsetWidth;
    element.classList.add("material-morph");
  });
}

function applyMaterial(material) {
  const metric = currentMetricCard();
  const palette = materialPalettes[material];
  if (palette) {
    const inputs = [document.querySelector("#colorA"), document.querySelector("#colorB"), document.querySelector("#colorC")];
    palette.forEach((color, index) => {
      inputs[index].value = color;
      inputs[index].nextElementSibling.textContent = color.toUpperCase();
    });
    [metric.dataset.colorA, metric.dataset.colorB, metric.dataset.colorC] = palette;
    [materialPreview, metric].forEach((element) => {
      element.style.setProperty("--mat-a", palette[0]);
      element.style.setProperty("--mat-b", palette[1]);
      element.style.setProperty("--mat-c", palette[2]);
    });
  }
  materialPreview.dataset.material = material;
  metric.dataset.material = material;
  document.querySelectorAll(".material-swatch").forEach((button) => button.classList.toggle("active", button.dataset.material === material));
  replayMaterialMorph();
}

function updateMaterialRanges() {
  const metric = currentMetricCard();
  const opacity = document.querySelector("#materialOpacity").value;
  const blur = document.querySelector("#materialBlur").value;
  const flow = document.querySelector("#flowSpeed").value;
  document.querySelector("#opacityOutput").textContent = `${opacity}%`;
  document.querySelector("#blurOutput").textContent = `${blur}px`;
  document.querySelector("#flowOutput").textContent = `${(flow / 100).toFixed(2)}×`;
  metric.dataset.opacity = opacity;
  metric.dataset.blur = blur;
  metric.dataset.flow = flow;
  [materialPreview, metric].forEach((element) => {
    element.style.setProperty("--material-opacity", opacity / 100);
    element.style.setProperty("--material-blur", `${blur}px`);
    element.style.setProperty("--flow-duration", `${Math.max(2.2, 8 - flow / 50)}s`);
  });
}

function updateCustomColors() {
  const metric = currentMetricCard();
  const inputs = [document.querySelector("#colorA"), document.querySelector("#colorB"), document.querySelector("#colorC")];
  const [colorA, colorB, colorC] = inputs.map((input) => input.value);
  inputs.forEach((input) => { input.nextElementSibling.textContent = input.value.toUpperCase(); });
  metric.dataset.colorA = colorA;
  metric.dataset.colorB = colorB;
  metric.dataset.colorC = colorC;
  [materialPreview, metric].forEach((element) => {
    element.style.setProperty("--mat-a", colorA);
    element.style.setProperty("--mat-b", colorB);
    element.style.setProperty("--mat-c", colorC);
  });
  applyMaterial("custom");
}

function syncMaterialDrawer() {
  const metric = currentMetricCard();
  const material = metric.dataset.material || "original";
  const styles = getComputedStyle(metric);
  const colorValues = [
    metric.dataset.colorA || styles.getPropertyValue("--mat-a").trim() || "#33ff4b",
    metric.dataset.colorB || styles.getPropertyValue("--mat-b").trim() || "#ff8539",
    metric.dataset.colorC || styles.getPropertyValue("--mat-c").trim() || "#11172b",
  ];
  const inputs = [document.querySelector("#colorA"), document.querySelector("#colorB"), document.querySelector("#colorC")];
  materialPreview.dataset.material = material;
  materialPreview.querySelector("strong").textContent = metric.querySelector("h3").textContent;
  inputs.forEach((input, index) => {
    input.value = colorValues[index];
    input.nextElementSibling.textContent = colorValues[index].toUpperCase();
    materialPreview.style.setProperty(`--mat-${String.fromCharCode(97 + index)}`, colorValues[index]);
  });
  document.querySelector("#materialOpacity").value = metric.dataset.opacity || 88;
  document.querySelector("#materialBlur").value = metric.dataset.blur || 18;
  document.querySelector("#flowSpeed").value = metric.dataset.flow || 200;
  document.querySelectorAll(".material-swatch").forEach((button) => button.classList.toggle("active", button.dataset.material === material));
  updateMaterialRanges();
  replayMaterialMorph();
}

function openMaterialDrawer() {
  materialCardSelect.value = String(selectedMetricIndex);
  syncMaterialDrawer();
  materialOverlay.setAttribute("aria-hidden", "false");
  document.querySelectorAll("[data-open-material]").forEach((button) => button.setAttribute("aria-expanded", "true"));
  document.body.classList.add("material-open");
  requestAnimationFrame(() => materialOverlay.classList.add("open"));
  window.setTimeout(() => document.querySelector("#closeMaterialBtn").focus(), 380);
}

function closeMaterialDrawer() {
  materialOverlay.classList.remove("open");
  materialOverlay.setAttribute("aria-hidden", "true");
  document.querySelectorAll("[data-open-material]").forEach((button) => button.setAttribute("aria-expanded", "false"));
  document.body.classList.remove("material-open");
  document.querySelector("#materialSettingsBtn").focus();
}

function resetMaterialControls(resetTheme = false) {
  const initial = initialMetricStates[Number(materialCardSelect.value) || 0];
  document.querySelector("#materialOpacity").value = initial.opacity;
  document.querySelector("#materialBlur").value = initial.blur;
  document.querySelector("#flowSpeed").value = initial.flow;
  if (resetTheme) {
    const metric = currentMetricCard();
    const inputs = [document.querySelector("#colorA"), document.querySelector("#colorB"), document.querySelector("#colorC")];
    initial.colors.forEach((color, index) => {
      inputs[index].value = color;
      inputs[index].nextElementSibling.textContent = color.toUpperCase();
      metric.style.setProperty(`--mat-${String.fromCharCode(97 + index)}`, color);
      metric.dataset[`color${String.fromCharCode(65 + index)}`] = color;
    });
    applyMaterial(initial.material);
  }
  updateMaterialRanges();
}

function bindEvents() {
  themeToggleBtn.addEventListener("click", () => {
    const themeOrder = ["system", "light", "dark"];
    const nextTheme = themeOrder[(themeOrder.indexOf(themePreference) + 1) % themeOrder.length];
    themeControl.classList.remove("theme-switching");
    void themeControl.offsetWidth;
    themeControl.classList.add("theme-switching");
    applyTheme(nextTheme, { announce: true });
    window.setTimeout(() => themeControl.classList.remove("theme-switching"), 460);
  });
  systemThemeQuery.addEventListener("change", () => {
    if (themePreference === "system") applyTheme("system", { persist: false });
  });
  document.querySelectorAll("[data-accent-option]").forEach((button) => button.addEventListener("click", () => {
    applyAccent(button.dataset.accentOption, { announce: true });
  }));
  metricCards.forEach((card, index) => {
    card.addEventListener("pointermove", (event) => {
      card.classList.add("hovering");
      const bounds = card.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
      const y = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height));
      card.style.setProperty("--pointer-x", `${x * 100}%`);
      card.style.setProperty("--pointer-y", `${y * 100}%`);
      card.style.setProperty("--metric-rx", `${(0.5 - y) * 5}deg`);
      card.style.setProperty("--metric-ry", `${(x - 0.5) * 7}deg`);
    });
    card.addEventListener("pointerleave", () => {
      card.classList.remove("hovering");
      card.style.setProperty("--metric-rx", "0deg");
      card.style.setProperty("--metric-ry", "0deg");
    });
    card.addEventListener("click", () => selectMetricCard(index, { announce: true }));
    card.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      selectMetricCard(index, { announce: true });
    });
  });
  orbitModeBtn.addEventListener("click", () => setViewMode("orbit"));
  fanModeBtn.addEventListener("click", () => setViewMode("fan"));
  playToggle.addEventListener("click", () => setPlaying(!isPlaying));
  document.querySelector("#prevBtn").addEventListener("click", () => nextCard(-1));
  document.querySelector("#nextBtn").addEventListener("click", () => nextCard(1));
  document.querySelector("#speedBtn").addEventListener("click", (event) => {
    speed = speed === 2 ? 1 : speed === 1 ? 0.5 : 2;
    event.currentTarget.textContent = `速度 ${speed}×`;
    restartAutoplay();
  });

  viewport.addEventListener("wheel", (event) => {
    event.preventDefault();
    let dominantDelta = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
    if (!dominantDelta) return;
    if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) dominantDelta *= 16;
    if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) dominantDelta *= viewport.clientHeight;
    const contribution = -Math.max(-140, Math.min(140, dominantDelta)) / 145;
    lastWheelDirection = Math.sign(contribution);
    targetPosition += contribution;
    startCarouselAnimation();
  }, { passive: false });

  viewport.addEventListener("pointerdown", (event) => {
    pointerStart = event.clientX;
    pointerCurrent = event.clientX;
    dragOriginPosition = visualPosition;
    if (carouselFrame !== null) cancelAnimationFrame(carouselFrame);
    carouselFrame = null;
    targetPosition = visualPosition;
    viewport.classList.add("dragging");
    viewport.classList.add("continuous-motion");
    if (autoplayTimer) cancelAnimationFrame(autoplayTimer);
    autoplayTimer = null;
  });
  viewport.addEventListener("pointermove", (event) => {
    if (pointerStart === null) return;
    pointerCurrent = event.clientX;
    const offset = Math.max(-240, Math.min(240, pointerCurrent - pointerStart));
    visualPosition = dragOriginPosition - offset / 112;
    targetPosition = visualPosition;
    scene.style.setProperty("--drag-tilt", `${offset * -.012}deg`);
    updateCardPositions(visualPosition);
  });
  viewport.addEventListener("pointerup", (event) => {
    if (pointerStart === null) return;
    const distance = event.clientX - pointerStart;
    let snapTarget = Math.round(visualPosition);
    if (Math.abs(distance) > 38) {
      const direction = distance > 0 ? -1 : 1;
      if (snapTarget === Math.round(dragOriginPosition)) snapTarget += direction;
      commitCarouselTarget(snapTarget, true, direction);
    } else if (!event.target.closest(".doc-card")) {
      const currentBounds = scene.querySelector(".doc-card.selected").getBoundingClientRect();
      if (event.clientX > currentBounds.right) commitCarouselTarget(Math.round(visualPosition) + 1, true, 1);
      else if (event.clientX < currentBounds.left) commitCarouselTarget(Math.round(visualPosition) - 1, true, -1);
      else commitCarouselTarget(snapTarget, true);
    } else {
      commitCarouselTarget(snapTarget, true);
    }
    pointerStart = null;
    pointerCurrent = null;
    viewport.classList.remove("dragging");
    scene.style.removeProperty("--drag-tilt");
    if (isPlaying) restartAutoplay();
  });
  viewport.addEventListener("pointercancel", () => {
    commitCarouselTarget(Math.round(visualPosition), true);
    pointerStart = null;
    pointerCurrent = null;
    viewport.classList.remove("dragging");
    scene.style.removeProperty("--drag-tilt");
    if (isPlaying) restartAutoplay();
  });
  viewport.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") nextCard(1);
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextCard(-1);
    if (event.key === " ") { event.preventDefault(); setPlaying(!isPlaying); }
  });

  document.querySelectorAll(".primary-nav .nav-item:not(.active):not([data-open-material])").forEach((button) => button.addEventListener("click", () => showToast(`${button.textContent.trim()} · 备考模块`)));
  document.querySelectorAll(".scene-actions button, .detail-actions button, .ai-note button, .scan-btn").forEach((button) => button.addEventListener("click", () => showToast(`${button.textContent.trim()}成功`)));
  document.querySelectorAll(".queue-tabs button").forEach((button) => button.addEventListener("click", () => {
    button.parentElement.querySelector(".active").classList.remove("active");
    button.classList.add("active");
  }));

  document.querySelectorAll("[data-open-material]").forEach((button) => button.addEventListener("click", openMaterialDrawer));
  document.querySelector("#closeMaterialBtn").addEventListener("click", () => closeMaterialDrawer());
  materialOverlay.addEventListener("pointerdown", (event) => {
    if (event.target === materialOverlay) closeMaterialDrawer();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && materialOverlay.classList.contains("open")) closeMaterialDrawer();
  });
  document.querySelectorAll(".material-swatch").forEach((button) => button.addEventListener("click", () => applyMaterial(button.dataset.material)));
  document.querySelectorAll(".color-fields input").forEach((input) => input.addEventListener("input", updateCustomColors));
  document.querySelectorAll(".material-controls input").forEach((input) => input.addEventListener("input", updateMaterialRanges));
  materialCardSelect.addEventListener("change", () => selectMetricCard(Number(materialCardSelect.value), { syncDrawer: true }));
  document.querySelector("#resetMaterialBtn").addEventListener("click", () => { resetMaterialControls(false); showToast("参数已重置"); });
  document.querySelector("#defaultMaterialBtn").addEventListener("click", () => { resetMaterialControls(true); showToast("已恢复初始材质"); });
  document.querySelector("#saveMaterialBtn").addEventListener("click", () => { closeMaterialDrawer(); showToast("材质设置已保存"); });
}

applyTheme(themePreference, { persist: false });
applyAccent(accentPreference, { persist: false });
renderQueue();
renderCards();
renderTimeline();
bindEvents();
selectMetricCard(0, { syncDrawer: false });
selectCard(selectedIndex);
setPlaying(true);
