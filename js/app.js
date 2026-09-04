/**
 * Wandoor Runners Dashboard Logic
 * Modern, Athletic, Clean Typography, Zero Emojis.
 * Supports:
 * 1. Day-by-Day View
 * 2. Zoho-Style Custom Date Range View (From - To)
 * 3. Overall 100k Challenge Leaderboard
 * 4. High-Resolution Image (PNG) Export
 * 5. Official Vector/Paginated PDF Export
 */

let clubData = null;
let currentTab = "daily"; // "daily" | "range" | "overall"
let selectedDate = null;
let rangeFromDate = null;
let rangeToDate = null;
let searchQuery = "";

// Strip all emojis, flags, icons from Strava athlete names
function cleanAthleteName(name) {
  if (!name) return "Runner";
  return name
    .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1F018}-\u{1F270}\u{2388}\u{200D}\u{FE0F}]/gu, '')
    .trim();
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadData();
  setupEventListeners();
  renderDashboard();
});

async function loadData() {
  try {
    const res = await fetch("data/club_history.json?t=" + Date.now());
    if (res.ok) {
      clubData = await res.json();
      document.getElementById("syncStatusLabel").textContent = "Daily Sync Active";
    } else {
      throw new Error("Local file not found");
    }
  } catch (e) {
    console.warn("Using fallback local seed:", e);
    clubData = getFallbackData();
    document.getElementById("syncStatusLabel").textContent = "Offline Preview";
  }

  const dates = clubData.dates || [];
  selectedDate = dates.length > 0 ? dates[dates.length - 1] : new Date().toISOString().split("T")[0];
  if (dates.length > 0) {
    rangeFromDate = dates[0];
    rangeToDate = dates[dates.length - 1];
  }
}

function setupEventListeners() {
  const tabDaily = document.getElementById("tabDaily");
  const tabRange = document.getElementById("tabRange");
  const tabOverall = document.getElementById("tabOverall");
  const dateFilterWrap = document.getElementById("dateFilterWrap");
  const dateRangeFilterWrap = document.getElementById("dateRangeFilterWrap");

  const setTab = (mode) => {
    currentTab = mode;
    tabDaily.classList.toggle("active", mode === "daily");
    tabRange.classList.toggle("active", mode === "range");
    tabOverall.classList.toggle("active", mode === "overall");

    if (dateFilterWrap) dateFilterWrap.style.display = (mode === "daily") ? "flex" : "none";
    if (dateRangeFilterWrap) dateRangeFilterWrap.style.display = (mode === "range") ? "flex" : "none";
    renderDashboard();
  };

  if (tabDaily) tabDaily.addEventListener("click", () => setTab("daily"));
  if (tabRange) tabRange.addEventListener("click", () => setTab("range"));
  if (tabOverall) tabOverall.addEventListener("click", () => setTab("overall"));

  const dateSelect = document.getElementById("dateSelect");
  if (dateSelect) {
    dateSelect.addEventListener("change", (e) => {
      selectedDate = e.target.value;
      renderDashboard();
    });
  }

  const rangeFromSelect = document.getElementById("rangeFromSelect");
  const rangeToSelect = document.getElementById("rangeToSelect");

  if (rangeFromSelect && rangeToSelect) {
    rangeFromSelect.addEventListener("change", (e) => {
      rangeFromDate = e.target.value;
      if (rangeFromDate > rangeToDate) {
        rangeToDate = rangeFromDate;
        rangeToSelect.value = rangeToDate;
      }
      renderDashboard();
    });

    rangeToSelect.addEventListener("change", (e) => {
      rangeToDate = e.target.value;
      if (rangeToDate < rangeFromDate) {
        rangeFromDate = rangeToDate;
        rangeFromSelect.value = rangeFromDate;
      }
      renderDashboard();
    });
  }

  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderTable();
    });
  }

  // Export action buttons
  const btnExportImage = document.getElementById("btnExportImage");
  if (btnExportImage) btnExportImage.addEventListener("click", exportAsImage);

  const btnExportPDF = document.getElementById("btnExportPDF");
  if (btnExportPDF) btnExportPDF.addEventListener("click", exportAsPDF);

  // WhatsApp modal
  const waModal = document.getElementById("whatsappModal");
  const btnOpenWhatsApp = document.getElementById("btnOpenWhatsApp");
  if (btnOpenWhatsApp && waModal) {
    btnOpenWhatsApp.addEventListener("click", () => {
      generateWhatsAppMessage();
      waModal.classList.add("open");
    });
  }
  const waCloseBtn = document.getElementById("waCloseBtn");
  if (waCloseBtn && waModal) waCloseBtn.addEventListener("click", () => waModal.classList.remove("open"));
  if (waModal) {
    waModal.addEventListener("click", (e) => {
      if (e.target.id === "whatsappModal") waModal.classList.remove("open");
    });
  }

  const btnCopyWhatsApp = document.getElementById("btnCopyWhatsApp");
  if (btnCopyWhatsApp) btnCopyWhatsApp.addEventListener("click", copyWhatsAppText);

  // Athlete modal
  const athleteModal = document.getElementById("athleteModal");
  const modalCloseBtn = document.getElementById("modalCloseBtn");
  if (modalCloseBtn && athleteModal) modalCloseBtn.addEventListener("click", () => athleteModal.classList.remove("open"));
  if (athleteModal) {
    athleteModal.addEventListener("click", (e) => {
      if (e.target.id === "athleteModal") athleteModal.classList.remove("open");
    });
  }
}

function renderDashboard() {
  populateDateDropdown();
  populateDateRangeDropdowns();
  renderKPIs();
  renderPodium();
  renderTable();
}

function getLocalISTDateStr() {
  try {
    return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
  } catch (e) {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  }
}

function populateDateDropdown() {
  const dateSelect = document.getElementById("dateSelect");
  if (!dateSelect) return;
  dateSelect.innerHTML = "";
  const dates = clubData.dates || [selectedDate];
  const todayStr = getLocalISTDateStr();

  [...dates].reverse().forEach(d => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = (d === todayStr) ? `Today (${d})` : d;
    if (d === selectedDate) opt.selected = true;
    dateSelect.appendChild(opt);
  });
}

function populateDateRangeDropdowns() {
  const fromSelect = document.getElementById("rangeFromSelect");
  const toSelect = document.getElementById("rangeToSelect");
  if (!fromSelect || !toSelect) return;

  const dates = clubData.dates || [];
  if (!rangeFromDate && dates.length > 0) rangeFromDate = dates[0];
  if (!rangeToDate && dates.length > 0) rangeToDate = dates[dates.length - 1];

  fromSelect.innerHTML = "";
  toSelect.innerHTML = "";

  dates.forEach(d => {
    const optFrom = document.createElement("option");
    optFrom.value = d;
    optFrom.textContent = d;
    if (d === rangeFromDate) optFrom.selected = true;
    fromSelect.appendChild(optFrom);

    const optTo = document.createElement("option");
    optTo.value = d;
    optTo.textContent = d;
    if (d === rangeToDate) optTo.selected = true;
    toSelect.appendChild(optTo);
  });
}

function getRangeAthletes(fromDate, toDate) {
  const athletes = Object.values(clubData.athlete_totals || {});
  const result = [];
  const targetKm = clubData.target_km || 100.0;

  athletes.forEach(a => {
    let rangeDist = 0.0;
    let rangeRuns = 0;
    const bd = a.daily_breakdown || {};

    for (const d of (clubData.dates || [])) {
      if (d >= fromDate && d <= toDate) {
        const dist = bd[d] || 0.0;
        if (dist > 0) {
          rangeDist += dist;
          rangeRuns += 1;
        }
      }
    }

    rangeDist = Math.round(rangeDist * 100) / 100;

    result.push({
      ...a,
      range_distance_km: rangeDist,
      range_runs: rangeRuns,
      range_active_days: rangeRuns,
      range_pct: Math.min(100, Math.round((rangeDist / targetKm) * 100))
    });
  });

  result.sort((a, b) => b.range_distance_km - a.range_distance_km);
  return result;
}

function renderKPIs() {
  const athleteTotals = clubData.athlete_totals || {};
  const athletes = Object.values(athleteTotals);
  const targetKm = clubData.target_km || 100.0;
  const kpiLabel = document.getElementById("kpiMileageLabel");
  const todayStr = getLocalISTDateStr();

  // Active Runners registered
  document.getElementById("kpiRunnersCount").textContent = athletes.length;

  if (currentTab === "daily") {
    const dailyLogs = (clubData.daily_records && clubData.daily_records[selectedDate]) || [];
    const totalDist = dailyLogs.reduce((sum, l) => sum + (l.daily_distance_km || 0), 0);
    const activeCount = dailyLogs.filter(l => l.daily_distance_km > 0).length;

    if (kpiLabel) {
      kpiLabel.textContent = (selectedDate === todayStr) ? "Club Mileage Today" : `Club Mileage (${selectedDate})`;
    }
    document.getElementById("kpiTodayDistance").innerHTML = `${totalDist.toFixed(1)} <span class="unit">km</span>`;
    document.getElementById("kpiTodayCount").textContent = `${activeCount} runners logged`;

  } else if (currentTab === "range") {
    const rangeAthletes = getRangeAthletes(rangeFromDate, rangeToDate);
    const totalDist = rangeAthletes.reduce((sum, a) => sum + (a.range_distance_km || 0), 0);
    const activeCount = rangeAthletes.filter(a => a.range_distance_km > 0).length;

    if (kpiLabel) {
      kpiLabel.textContent = `Club Mileage (${rangeFromDate.slice(5)} to ${rangeToDate.slice(5)})`;
    }
    document.getElementById("kpiTodayDistance").innerHTML = `${totalDist.toFixed(1)} <span class="unit">km</span>`;
    document.getElementById("kpiTodayCount").textContent = `${activeCount} runners active`;

  } else {
    // 100k Challenge Overall
    const totalDist = athletes.reduce((sum, a) => sum + (a.total_challenge_km || 0), 0);
    const activeCount = athletes.filter(a => a.total_challenge_km > 0).length;

    if (kpiLabel) {
      kpiLabel.textContent = "Total Challenge Mileage";
    }
    document.getElementById("kpiTodayDistance").innerHTML = `${totalDist.toFixed(1)} <span class="unit">km</span>`;
    document.getElementById("kpiTodayCount").textContent = `${activeCount} active participants`;
  }

  // Finishers Count (>= 100km)
  const finishers = athletes.filter(a => (a.total_challenge_km || 0) >= targetKm);
  document.getElementById("kpiFinishersCount").textContent = finishers.length;
}

function renderPodium() {
  const grid = document.getElementById("podiumGrid");
  const titleEl = document.querySelector(".podium-title");
  if (!grid) return;
  grid.innerHTML = "";

  let podiumAthletes = [];
  let distKey = "total_challenge_km";

  if (currentTab === "daily") {
    const dailyLogs = (clubData.daily_records && clubData.daily_records[selectedDate]) || [];
    podiumAthletes = [...dailyLogs].filter(l => l.daily_distance_km > 0);
    distKey = "daily_distance_km";
    if (titleEl) {
      titleEl.innerHTML = `<svg viewBox="0 0 24 24"><path d="M19 5h-2V3H7v2H5c-1.1 0-2 .9-2 2v1c0 2.55 1.92 4.63 4.39 4.94.63 1.5 1.98 2.63 3.61 2.96V19H7v2h10v-2h-4v-3.1c1.63-.33 2.98-1.46 3.61-2.96C19.08 12.63 21 10.55 21 8V7c0-1.1-.9-2-2-2zM5 8V7h2v3.82C5.84 10.4 5 9.3 5 8zm14 0c0 1.3-.84 2.4-2 2.82V7h2v1z"/></svg> Top Performers (${selectedDate})`;
    }
  } else if (currentTab === "range") {
    const rangeList = getRangeAthletes(rangeFromDate, rangeToDate);
    podiumAthletes = rangeList.filter(a => a.range_distance_km > 0);
    distKey = "range_distance_km";
    if (titleEl) {
      titleEl.innerHTML = `<svg viewBox="0 0 24 24"><path d="M19 5h-2V3H7v2H5c-1.1 0-2 .9-2 2v1c0 2.55 1.92 4.63 4.39 4.94.63 1.5 1.98 2.63 3.61 2.96V19H7v2h10v-2h-4v-3.1c1.63-.33 2.98-1.46 3.61-2.96C19.08 12.63 21 10.55 21 8V7c0-1.1-.9-2-2-2zM5 8V7h2v3.82C5.84 10.4 5 9.3 5 8zm14 0c0 1.3-.84 2.4-2 2.82V7h2v1z"/></svg> Range Leaders (${rangeFromDate.slice(5)} - ${rangeToDate.slice(5)})`;
    }
  } else {
    const athletes = Object.values(clubData.athlete_totals || {});
    athletes.sort((a, b) => b.total_challenge_km - a.total_challenge_km);
    podiumAthletes = athletes;
    distKey = "total_challenge_km";
    if (titleEl) {
      titleEl.innerHTML = `<svg viewBox="0 0 24 24"><path d="M19 5h-2V3H7v2H5c-1.1 0-2 .9-2 2v1c0 2.55 1.92 4.63 4.39 4.94.63 1.5 1.98 2.63 3.61 2.96V19H7v2h10v-2h-4v-3.1c1.63-.33 2.98-1.46 3.61-2.96C19.08 12.63 21 10.55 21 8V7c0-1.1-.9-2-2-2zM5 8V7h2v3.82C5.84 10.4 5 9.3 5 8zm14 0c0 1.3-.84 2.4-2 2.82V7h2v1z"/></svg> Current Challenge Leaders`;
    }
  }

  if (podiumAthletes.length < 3) return;

  const top1 = podiumAthletes[0];
  const top2 = podiumAthletes[1];
  const top3 = podiumAthletes[2];

  const podiumOrder = [
    { athlete: top2, rank: 2, badgeClass: "rank-silver", label: "2nd Place" },
    { athlete: top1, rank: 1, badgeClass: "rank-gold", label: "Leading" },
    { athlete: top3, rank: 3, badgeClass: "rank-bronze", label: "3rd Place" }
  ];

  podiumOrder.forEach(item => {
    const a = item.athlete;
    const cleanName = cleanAthleteName(a.name);
    const dist = (a[distKey] || 0).toFixed(1);
    const subText = (currentTab === "daily") 
      ? (a.avg_pace && a.avg_pace !== '--' ? `${a.avg_pace} /km` : "Top Run") 
      : `${a.pct_completed || a.range_pct || 0}% of 100k`;

    const card = document.createElement("div");
    card.className = `podium-card ${item.badgeClass}`;
    card.innerHTML = `
      <div class="podium-badge">${item.rank}</div>
      <img src="${a.avatar_url || 'https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'}" 
           onerror="this.src='https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'" 
           class="podium-avatar" alt="">
      <div class="podium-name" title="${cleanName}">${cleanName}</div>
      <div class="podium-km">${dist} <span style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">km</span></div>
      <div class="podium-pct">${subText}</div>
    `;
    card.addEventListener("click", () => openAthleteModal(a.athlete_id));
    grid.appendChild(card);
  });
}

function renderTable() {
  const thead = document.getElementById("tableHeaderRow");
  const tbody = document.getElementById("tableBody");
  if (!thead || !tbody) return;
  tbody.innerHTML = "";

  const chartIconSvg = `<svg viewBox="0 0 24 24"><path d="M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z"/></svg>`;

  if (currentTab === "daily") {
    // Day-by-Day columns
    thead.innerHTML = `
      <th style="width: 44px; text-align: center;">Rank</th>
      <th>Athlete</th>
      <th style="text-align: right;">Distance</th>
      <th class="col-hide-mobile" style="text-align: center; width: 60px;">Runs</th>
      <th class="col-hide-mobile" style="width: 100px;">Avg. Pace</th>
      <th class="col-hide-mobile" style="width: 80px;">Elevation</th>
      <th class="col-hide-mobile" style="width: 90px;">Week Total</th>
      <th class="col-hide-mobile" style="text-align: right; width: 85px;">Details</th>
    `;

    const dailyLogs = (clubData.daily_records && clubData.daily_records[selectedDate]) || [];
    let filtered = dailyLogs.filter(l => {
      if (!searchQuery) return true;
      const name = cleanAthleteName(l.name).toLowerCase();
      const totalInfo = (clubData.athlete_totals && clubData.athlete_totals[l.athlete_id]) || {};
      const excelName = (totalInfo.excel_name || "").toLowerCase();
      const mob = (totalInfo.mobile || "").replace(/\s+/g, "");
      const cleanQ = searchQuery.replace(/\s+/g, "");
      const sl = totalInfo.sl_no ? String(totalInfo.sl_no) : "";
      return name.includes(searchQuery) || excelName.includes(searchQuery) || mob.includes(cleanQ) || sl === searchQuery;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 28px;">No activity logged for this date.</td></tr>`;
      return;
    }

    filtered.forEach((r, idx) => {
      const tr = document.createElement("tr");
      const cleanName = cleanAthleteName(r.name);

      let rankClass = "rank-num";
      if (idx === 0) rankClass += " rank-top-1";
      else if (idx === 1) rankClass += " rank-top-2";
      else if (idx === 2) rankClass += " rank-top-3";

      const paceText = (r.avg_pace && r.avg_pace !== '--') ? `${r.avg_pace} /km` : '--';

      tr.innerHTML = `
        <td style="text-align: center;"><span class="${rankClass}">#${idx + 1}</span></td>
        <td>
          <div class="athlete-profile">
            <img src="${r.avatar_url || 'https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'}" 
                 onerror="this.src='https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'" 
                 class="athlete-photo" alt="">
            <span class="athlete-title-name" title="${cleanName}">${cleanName}</span>
          </div>
        </td>
        <td style="text-align: right;">
          <div class="stat-cell-stack">
            <span class="distance-bold">${r.daily_distance_km.toFixed(1)} <span class="unit-gray">km</span></span>
            <span class="mobile-only-sub">${paceText}</span>
          </div>
        </td>
        <td class="col-hide-mobile" style="text-align: center;">${r.daily_distance_km > 0 ? (r.daily_runs || 1) : 0}</td>
        <td class="col-hide-mobile">${paceText}</td>
        <td class="col-hide-mobile">${r.daily_elev_gain_m || 0} <span class="unit-gray">m</span></td>
        <td class="col-hide-mobile" style="color: var(--text-secondary); font-weight: 500;">${(r.weekly_cumulative_km || 0).toFixed(1)} km</td>
        <td class="col-hide-mobile" style="text-align: right;">
          <button class="btn-details">${chartIconSvg}Days</button>
        </td>
      `;

      tr.addEventListener("click", () => openAthleteModal(r.athlete_id));
      tbody.appendChild(tr);
    });

  } else if (currentTab === "range") {
    // Date Range View columns
    thead.innerHTML = `
      <th style="width: 44px; text-align: center;">Rank</th>
      <th>Athlete</th>
      <th style="text-align: right;">Range Distance</th>
      <th class="col-hide-mobile" style="text-align: center; width: 80px;">Active Days</th>
      <th class="col-hide-mobile" style="text-align: right; width: 100px;">100k Total</th>
      <th class="col-hide-mobile" style="text-align: right; width: 90px;">% of 100k</th>
      <th class="col-hide-mobile" style="text-align: right; width: 85px;">Details</th>
    `;

    const rangeAthletes = getRangeAthletes(rangeFromDate, rangeToDate);
    let filtered = rangeAthletes.filter(a => {
      if (!searchQuery) return true;
      const name = cleanAthleteName(a.name).toLowerCase();
      const excelName = (a.excel_name || "").toLowerCase();
      const mob = (a.mobile || "").replace(/\s+/g, "");
      const cleanQ = searchQuery.replace(/\s+/g, "");
      const sl = a.sl_no ? String(a.sl_no) : "";
      return name.includes(searchQuery) || excelName.includes(searchQuery) || mob.includes(cleanQ) || sl === searchQuery;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 28px;">No activity logged for this date range.</td></tr>`;
      return;
    }

    filtered.forEach((a, idx) => {
      const tr = document.createElement("tr");
      const cleanName = cleanAthleteName(a.name);
      const pct = Math.min(100, Math.round((a.total_challenge_km / (clubData.target_km || 100.0)) * 100));

      let rankClass = "rank-num";
      if (idx === 0) rankClass += " rank-top-1";
      else if (idx === 1) rankClass += " rank-top-2";
      else if (idx === 2) rankClass += " rank-top-3";

      tr.innerHTML = `
        <td style="text-align: center;"><span class="${rankClass}">#${idx + 1}</span></td>
        <td>
          <div class="athlete-profile">
            <img src="${a.avatar_url || 'https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'}" 
                 onerror="this.src='https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'" 
                 class="athlete-photo" alt="">
            <span class="athlete-title-name" title="${cleanName}">${cleanName}</span>
          </div>
        </td>
        <td style="text-align: right;">
          <div class="stat-cell-stack">
            <span class="distance-bold">${a.range_distance_km.toFixed(1)} <span class="unit-gray">km</span></span>
            <span class="mobile-only-sub">${a.range_active_days} active days</span>
          </div>
        </td>
        <td class="col-hide-mobile" style="text-align: center; font-weight: 600;">${a.range_active_days}d</td>
        <td class="col-hide-mobile" style="text-align: right; color: var(--text-secondary); font-weight: 600;">${a.total_challenge_km.toFixed(1)} km</td>
        <td class="col-hide-mobile" style="text-align: right; font-weight: 700; color: var(--primary-orange);">${pct}%</td>
        <td class="col-hide-mobile" style="text-align: right;">
          <button class="btn-details">${chartIconSvg}Days</button>
        </td>
      `;

      tr.addEventListener("click", () => openAthleteModal(a.athlete_id));
      tbody.appendChild(tr);
    });

  } else {
    // 100k Challenge Leaderboard columns
    thead.innerHTML = `
      <th style="width: 44px; text-align: center;">Rank</th>
      <th>Athlete</th>
      <th style="text-align: right;">100k Progress</th>
      <th class="col-hide-mobile" style="text-align: right; width: 90px;">Total</th>
      <th class="col-hide-mobile" style="text-align: right; width: 90px;">Remaining</th>
      <th class="col-hide-mobile" style="text-align: center; width: 70px;">Days</th>
      <th class="col-hide-mobile" style="width: 80px;">Status</th>
      <th class="col-hide-mobile" style="text-align: right; width: 85px;">Details</th>
    `;

    const targetKm = clubData.target_km || 100.0;
    const athletes = Object.values(clubData.athlete_totals || {});
    athletes.sort((a, b) => b.total_challenge_km - a.total_challenge_km);

    let filtered = athletes.filter(a => {
      if (!searchQuery) return true;
      const name = cleanAthleteName(a.name).toLowerCase();
      const excelName = (a.excel_name || "").toLowerCase();
      const mob = (a.mobile || "").replace(/\s+/g, "");
      const cleanQ = searchQuery.replace(/\s+/g, "");
      const sl = a.sl_no ? String(a.sl_no) : "";
      return name.includes(searchQuery) || excelName.includes(searchQuery) || mob.includes(cleanQ) || sl === searchQuery;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 28px;">No runners found.</td></tr>`;
      return;
    }

    filtered.forEach((a, idx) => {
      const tr = document.createElement("tr");
      const cleanName = cleanAthleteName(a.name);
      const pct = Math.min(100, Math.round((a.total_challenge_km / targetKm) * 100));
      const isDone = a.total_challenge_km >= targetKm;
      const remaining = Math.max(0, targetKm - a.total_challenge_km).toFixed(1);

      let rankClass = "rank-num";
      if (idx === 0) rankClass += " rank-top-1";
      else if (idx === 1) rankClass += " rank-top-2";
      else if (idx === 2) rankClass += " rank-top-3";

      let statusBadge = `<span class="status-tag active">Active</span>`;
      if (isDone) statusBadge = `<span class="status-tag finisher">Finisher</span>`;
      else if (pct >= 50) statusBadge = `<span class="status-tag ontrack">On Track</span>`;

      tr.innerHTML = `
        <td style="text-align: center;"><span class="${rankClass}">#${idx + 1}</span></td>
        <td>
          <div class="athlete-profile">
            <img src="${a.avatar_url || 'https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'}" 
                 onerror="this.src='https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'" 
                 class="athlete-photo" alt="">
            <span class="athlete-title-name" title="${cleanName}">${cleanName}</span>
          </div>
        </td>
        <td style="text-align: right;">
          <div class="stat-cell-stack">
            <span class="distance-bold">${a.total_challenge_km.toFixed(1)} <span class="unit-gray">km</span></span>
            <div class="progress-track-bg" style="height: 4px; margin-top: 3px; width: 100%;">
              <div class="progress-fill-bar ${isDone ? 'complete' : ''}" style="width: ${pct}%"></div>
            </div>
            <span class="mobile-only-sub">${pct}% of 100k</span>
          </div>
        </td>
        <td class="col-hide-mobile" style="text-align: right;"><span class="distance-bold">${a.total_challenge_km.toFixed(1)}</span> <span class="unit-gray">km</span></td>
        <td class="col-hide-mobile" style="text-align: right;">${remaining} <span class="unit-gray">km</span></td>
        <td class="col-hide-mobile" style="text-align: center;">${a.active_days || 0}d</td>
        <td class="col-hide-mobile">${statusBadge}</td>
        <td class="col-hide-mobile" style="text-align: right;">
          <button class="btn-details">${chartIconSvg}Days</button>
        </td>
      `;

      tr.addEventListener("click", () => openAthleteModal(a.athlete_id));
      tbody.appendChild(tr);
    });
  }
}

function openAthleteModal(athleteId) {
  const athlete = (clubData.athlete_totals && clubData.athlete_totals[athleteId]);
  if (!athlete) return;

  const cleanName = cleanAthleteName(athlete.name);

  document.getElementById("modalName").textContent = cleanName;
  document.getElementById("modalAvatar").src = athlete.avatar_url || "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png";
  document.getElementById("modalTotalDist").textContent = `${athlete.total_challenge_km.toFixed(1)} km`;
  document.getElementById("modalPct").textContent = `${athlete.pct_completed || 0}%`;
  document.getElementById("modalBestDay").textContent = `${athlete.best_day_km ? athlete.best_day_km.toFixed(1) : '0.0'} km`;
  const streakText = (athlete.current_streak && athlete.current_streak > 0) ? ` (${athlete.current_streak}d streak)` : "";
  document.getElementById("modalStreak").textContent = `${athlete.active_days || 0} active days${streakText}`;

  const tbody = document.getElementById("modalHistoryTbody");
  tbody.innerHTML = "";
  const barChart = document.getElementById("modalBarChart");
  barChart.innerHTML = "";

  const dates = clubData.dates || [];
  const userLogs = [];

  dates.forEach(d => {
    const logs = clubData.daily_records[d] || [];
    const log = logs.find(l => String(l.athlete_id) === String(athleteId));
    if (log && log.daily_distance_km > 0) {
      userLogs.push(log);
    }
  });

  if (userLogs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 14px;">No individual runs logged yet.</td></tr>`;
    barChart.innerHTML = `<span style="font-size: 11.5px; color: var(--text-muted); margin: auto;">No activity recorded yet</span>`;
  } else {
    const maxDist = Math.max(...userLogs.map(l => l.daily_distance_km), 5.0);
    userLogs.forEach(l => {
      const heightPct = Math.min(100, Math.round((l.daily_distance_km / maxDist) * 100));
      const col = document.createElement("div");
      col.style.cssText = "flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; min-width: 32px;";
      col.innerHTML = `
        <span style="font-size: 9.5px; font-weight: 700; color: var(--primary-orange); margin-bottom: 3px;">${l.daily_distance_km.toFixed(1)}k</span>
        <div style="width: 100%; height: ${heightPct}%; background: var(--primary-orange); border-radius: 3px 3px 0 0;"></div>
        <span style="font-size: 9px; color: var(--text-secondary); margin-top: 4px; white-space: nowrap;">${l.date.slice(5)}</span>
      `;
      barChart.appendChild(col);
    });

    [...userLogs].reverse().forEach(l => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${l.date}</td>
        <td style="font-weight: 700; color: var(--primary-orange);">${l.daily_distance_km.toFixed(1)} km</td>
        <td>${l.avg_pace || '--'}/km</td>
        <td>${l.daily_runs || 1}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  document.getElementById("athleteModal").classList.add("open");
}

function generateWhatsAppMessage() {
  let title = "";
  let list = [];
  let totalKm = 0;

  if (currentTab === "daily") {
    title = `*WANDOOR RUNNERS - DAILY REPORT*\nDate: ${selectedDate}`;
    const dailyLogs = (clubData.daily_records && clubData.daily_records[selectedDate]) || [];
    list = [...dailyLogs].filter(l => l.daily_distance_km > 0).slice(0, 10);
    totalKm = dailyLogs.reduce((sum, l) => sum + (l.daily_distance_km || 0), 0);
  } else if (currentTab === "range") {
    title = `*WANDOOR RUNNERS - DATE RANGE REPORT*\nPeriod: ${rangeFromDate} to ${rangeToDate}`;
    const rangeList = getRangeAthletes(rangeFromDate, rangeToDate);
    list = rangeList.filter(a => a.range_distance_km > 0).slice(0, 10);
    totalKm = rangeList.reduce((sum, a) => sum + (a.range_distance_km || 0), 0);
  } else {
    title = `*WANDOOR RUNNERS - 100K LEADERBOARD*`;
    const athletes = Object.values(clubData.athlete_totals || {});
    athletes.sort((a, b) => b.total_challenge_km - a.total_challenge_km);
    list = athletes.slice(0, 10);
    totalKm = athletes.reduce((sum, a) => sum + (a.total_challenge_km || 0), 0);
  }

  let msg = `${title}\n\n*Top Performers:*\n`;
  if (list.length === 0) {
    msg += `No runs logged yet for this period.\n`;
  } else {
    list.forEach((r, idx) => {
      const cleanName = cleanAthleteName(r.name);
      const km = (currentTab === "daily" ? r.daily_distance_km : (currentTab === "range" ? r.range_distance_km : r.total_challenge_km)).toFixed(1);
      msg += `${idx + 1}. *${cleanName}* - ${km} km\n`;
    });
  }

  msg += `\n*Club Total:* ${totalKm.toFixed(1)} km\n`;
  msg += `Challenge Target: 100 km\n`;
  msg += `View Live Dashboard: https://amigo12345as.github.io/wandoor-runners-100k/\n`;

  document.getElementById("whatsappText").value = msg;
}

function copyWhatsAppText() {
  const ta = document.getElementById("whatsappText");
  const btn = document.getElementById("btnCopyWhatsApp");
  const orig = btn.innerHTML;

  const showCopied = () => {
    btn.innerHTML = "Copied!";
    setTimeout(() => { btn.innerHTML = orig; }, 2000);
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(ta.value).then(showCopied).catch(() => {
      ta.select();
      document.execCommand("copy");
      showCopied();
    });
  } else {
    ta.select();
    document.execCommand("copy");
    showCopied();
  }
}

// Build off-screen high-contrast athletic document for Image / PDF export
function buildExportDOM() {
  const container = document.createElement("div");
  container.style.cssText = `
    position: fixed;
    left: -9999px;
    top: 0;
    width: 860px;
    background: #0D1117;
    color: #F0F6FC;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    padding: 32px;
    border-radius: 12px;
    box-sizing: border-box;
  `;

  let modeTitle = "";
  let subTitle = "";
  let athletesList = [];
  let distColName = "Distance";
  let distGetter = (a) => a.total_challenge_km;
  let subGetter = (a) => `${a.pct_completed || 0}% of 100k`;

  if (currentTab === "daily") {
    modeTitle = "DAILY LEADERBOARD REPORT";
    subTitle = `Official Day Runs • ${selectedDate}`;
    const dailyLogs = (clubData.daily_records && clubData.daily_records[selectedDate]) || [];
    athletesList = dailyLogs.filter(l => l.daily_distance_km > 0);
    distColName = "Today";
    distGetter = (l) => l.daily_distance_km;
    subGetter = (l) => (l.avg_pace && l.avg_pace !== '--') ? `${l.avg_pace} /km` : '--';
  } else if (currentTab === "range") {
    modeTitle = "DATE RANGE LEADERBOARD REPORT";
    subTitle = `Period: ${rangeFromDate} to ${rangeToDate}`;
    const rangeAthletes = getRangeAthletes(rangeFromDate, rangeToDate);
    athletesList = rangeAthletes.filter(a => a.range_distance_km > 0);
    distColName = "Range Distance";
    distGetter = (a) => a.range_distance_km;
    subGetter = (a) => `${a.range_active_days} active days`;
  } else {
    modeTitle = "OVERALL 100K CHALLENGE LEADERBOARD";
    subTitle = "Cumulative Standings • Target: 100.0 km";
    const athletes = Object.values(clubData.athlete_totals || {});
    athletes.sort((a, b) => b.total_challenge_km - a.total_challenge_km);
    athletesList = athletes;
    distColName = "Total Distance";
    distGetter = (a) => a.total_challenge_km;
    subGetter = (a) => `${a.pct_completed || 0}% completed`;
  }

  const totalKm = athletesList.reduce((sum, a) => sum + (distGetter(a) || 0), 0);
  const activeCount = athletesList.length;
  const topDist = athletesList.length > 0 ? distGetter(athletesList[0]).toFixed(1) : "0.0";
  const nowIST = new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" });

  let podiumHTML = "";
  if (athletesList.length >= 3) {
    const p1 = athletesList[0];
    const p2 = athletesList[1];
    const p3 = athletesList[2];
    podiumHTML = `
      <div style="display: flex; gap: 14px; margin-bottom: 24px;">
        <div style="flex: 1; background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px; text-align: center;">
          <div style="display: inline-block; width: 24px; height: 24px; border-radius: 50%; background: #30363D; color: #8B949E; font-weight: 800; font-size: 12px; line-height: 24px; margin-bottom: 6px;">2</div>
          <div style="font-weight: 700; font-size: 13px; color: #FFFFFF; margin-bottom: 4px;">${cleanAthleteName(p2.name)}</div>
          <div style="font-weight: 800; font-size: 16px; color: #FC5200;">${distGetter(p2).toFixed(1)} <span style="font-size: 11px; color: #8B949E;">km</span></div>
          <div style="font-size: 10px; color: #8B949E;">${subGetter(p2)}</div>
        </div>
        <div style="flex: 1.1; background: #1F1914; border: 1px solid #D29922; border-radius: 8px; padding: 16px; text-align: center;">
          <div style="display: inline-block; width: 28px; height: 28px; border-radius: 50%; background: #D29922; color: #0D1117; font-weight: 900; font-size: 14px; line-height: 28px; margin-bottom: 6px;">1</div>
          <div style="font-weight: 800; font-size: 14px; color: #FFFFFF; margin-bottom: 4px;">${cleanAthleteName(p1.name)}</div>
          <div style="font-weight: 900; font-size: 19px; color: #FC5200;">${distGetter(p1).toFixed(1)} <span style="font-size: 12px; color: #8B949E;">km</span></div>
          <div style="font-size: 10.5px; color: #D29922; font-weight: 600;">Leader • ${subGetter(p1)}</div>
        </div>
        <div style="flex: 1; background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px; text-align: center;">
          <div style="display: inline-block; width: 24px; height: 24px; border-radius: 50%; background: #9E6A03; color: #FFFFFF; font-weight: 800; font-size: 12px; line-height: 24px; margin-bottom: 6px;">3</div>
          <div style="font-weight: 700; font-size: 13px; color: #FFFFFF; margin-bottom: 4px;">${cleanAthleteName(p3.name)}</div>
          <div style="font-weight: 800; font-size: 16px; color: #FC5200;">${distGetter(p3).toFixed(1)} <span style="font-size: 11px; color: #8B949E;">km</span></div>
          <div style="font-size: 10px; color: #8B949E;">${subGetter(p3)}</div>
        </div>
      </div>
    `;
  }

  let rowsHTML = "";
  athletesList.forEach((a, idx) => {
    const cleanName = cleanAthleteName(a.name);
    const dist = distGetter(a).toFixed(1);
    const sub = subGetter(a);
    const rank = idx + 1;
    let rankColor = "#8B949E";
    if (rank === 1) rankColor = "#E3B341";
    else if (rank === 2) rankColor = "#C9D1D9";
    else if (rank === 3) rankColor = "#DB6D28";

    rowsHTML += `
      <tr style="border-bottom: 1px solid #21262D;">
        <td style="padding: 9px 12px; font-weight: 800; font-size: 12.5px; color: ${rankColor}; text-align: center; width: 44px;">#${rank}</td>
        <td style="padding: 9px 12px; font-weight: 600; font-size: 13px; color: #F0F6FC;">${cleanName}</td>
        <td style="padding: 9px 12px; font-weight: 800; font-size: 14px; color: #FC5200; text-align: right;">${dist} <span style="font-size: 10px; color: #8B949E; font-weight: 500;">km</span></td>
        <td style="padding: 9px 12px; font-size: 11.5px; color: #8B949E; text-align: right;">${sub}</td>
      </tr>
    `;
  });

  container.innerHTML = `
    <!-- Header -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #FC5200; padding-bottom: 16px; margin-bottom: 20px;">
      <div style="display: flex; align-items: center; gap: 14px;">
        <div style="width: 44px; height: 44px; border-radius: 8px; background: #FC5200; color: #FFFFFF; font-weight: 900; font-size: 18px; display: flex; align-items: center; justify-content: center; letter-spacing: -0.5px;">WR</div>
        <div>
          <div style="font-weight: 900; font-size: 20px; color: #FFFFFF; letter-spacing: 0.3px;">WANDOOR RUNNERS</div>
          <div style="font-size: 12px; font-weight: 600; color: #FC5200; text-transform: uppercase; letter-spacing: 0.5px;">Monsoon 100k Challenge 2026</div>
        </div>
      </div>
      <div style="text-align: right;">
        <div style="font-weight: 800; font-size: 13px; color: #FFFFFF;">${modeTitle}</div>
        <div style="font-size: 11px; color: #8B949E; margin-top: 2px;">${subTitle}</div>
        <div style="font-size: 9.5px; color: #6E7681; margin-top: 4px;">Generated: ${nowIST} IST</div>
      </div>
    </div>

    <!-- Summary Stats Strip -->
    <div style="display: flex; gap: 12px; margin-bottom: 22px;">
      <div style="flex: 1; background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 14px;">
        <div style="font-size: 10px; font-weight: 700; color: #8B949E; text-transform: uppercase;">Total Distance</div>
        <div style="font-size: 18px; font-weight: 900; color: #FC5200; margin-top: 2px;">${totalKm.toFixed(1)} <span style="font-size: 11px; color: #8B949E;">km</span></div>
      </div>
      <div style="flex: 1; background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 14px;">
        <div style="font-size: 10px; font-weight: 700; color: #8B949E; text-transform: uppercase;">Active Athletes</div>
        <div style="font-size: 18px; font-weight: 900; color: #FFFFFF; margin-top: 2px;">${activeCount}</div>
      </div>
      <div style="flex: 1; background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 14px;">
        <div style="font-size: 10px; font-weight: 700; color: #8B949E; text-transform: uppercase;">Leading Distance</div>
        <div style="font-size: 18px; font-weight: 900; color: #E3B341; margin-top: 2px;">${topDist} <span style="font-size: 11px; color: #8B949E;">km</span></div>
      </div>
      <div style="flex: 1; background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 14px;">
        <div style="font-size: 10px; font-weight: 700; color: #8B949E; text-transform: uppercase;">Challenge Target</div>
        <div style="font-size: 18px; font-weight: 900; color: #FFFFFF; margin-top: 2px;">100 <span style="font-size: 11px; color: #8B949E;">km</span></div>
      </div>
    </div>

    ${podiumHTML}

    <!-- Table -->
    <table style="width: 100%; border-collapse: collapse; background: #161B22; border: 1px solid #30363D; border-radius: 8px; overflow: hidden; margin-bottom: 20px;">
      <thead>
        <tr style="background: #21262D; border-bottom: 1px solid #30363D;">
          <th style="padding: 10px 12px; font-size: 11px; font-weight: 800; color: #8B949E; text-align: center; text-transform: uppercase; width: 44px;">Rank</th>
          <th style="padding: 10px 12px; font-size: 11px; font-weight: 800; color: #8B949E; text-align: left; text-transform: uppercase;">Athlete</th>
          <th style="padding: 10px 12px; font-size: 11px; font-weight: 800; color: #8B949E; text-align: right; text-transform: uppercase;">${distColName}</th>
          <th style="padding: 10px 12px; font-size: 11px; font-weight: 800; color: #8B949E; text-align: right; text-transform: uppercase;">Details / Status</th>
        </tr>
      </thead>
      <tbody>
        ${rowsHTML || `<tr><td colspan="4" style="text-align: center; padding: 24px; color: #8B949E;">No activity logged for this period.</td></tr>`}
      </tbody>
    </table>

    <!-- Footer -->
    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #30363D; padding-top: 14px; font-size: 10.5px; color: #8B949E;">
      <div>Wandoor Runners &bull; Automated Tracking with Strava Club API</div>
      <div style="color: #FC5200; font-weight: 600;">https://amigo12345as.github.io/wandoor-runners-100k/</div>
    </div>
  `;

  return container;
}

async function exportAsImage() {
  if (typeof window.html2canvas !== "function") {
    alert("Export library is still loading. Please try again in a moment.");
    return;
  }

  const btn = document.getElementById("btnExportImage");
  const origHtml = btn.innerHTML;
  btn.innerHTML = `<span style="font-size:10.5px;">Rendering...</span>`;
  btn.disabled = true;

  try {
    const container = buildExportDOM();
    document.body.appendChild(container);

    const canvas = await window.html2canvas(container, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: "#0D1117"
    });

    document.body.removeChild(container);

    const link = document.createElement("a");
    const modeTag = currentTab === "daily" 
      ? `daily-${selectedDate}` 
      : (currentTab === "range" ? `range-${rangeFromDate}-to-${rangeToDate}` : "overall-100k");
    link.download = `wandoor-runners-${modeTag}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  } catch (err) {
    console.error("Export Image error:", err);
    alert("Could not generate image. Please try again.");
  } finally {
    btn.innerHTML = origHtml;
    btn.disabled = false;
  }
}

async function exportAsPDF() {
  if (typeof window.html2canvas !== "function" || !window.jspdf || !window.jspdf.jsPDF) {
    alert("PDF export library is still loading. Please try again in a moment.");
    return;
  }

  const btn = document.getElementById("btnExportPDF");
  const origHtml = btn.innerHTML;
  btn.innerHTML = `<span style="font-size:10.5px;">Creating PDF...</span>`;
  btn.disabled = true;

  try {
    const container = buildExportDOM();
    document.body.appendChild(container);

    const canvas = await window.html2canvas(container, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: "#0D1117"
    });

    document.body.removeChild(container);

    const imgData = canvas.toDataURL("image/png");
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF("p", "mm", "a4");
    const pageWidth = 210;
    const pageHeight = 297;
    const imgWidth = pageWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    let heightLeft = imgHeight;
    let position = 0;

    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    while (heightLeft > 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
    }

    const modeTag = currentTab === "daily" 
      ? `daily-${selectedDate}` 
      : (currentTab === "range" ? `range-${rangeFromDate}-to-${rangeToDate}` : "overall-100k");
    pdf.save(`wandoor-runners-${modeTag}.pdf`);
  } catch (err) {
    console.error("Export PDF error:", err);
    alert("Could not generate PDF. Please try again.");
  } finally {
    btn.innerHTML = origHtml;
    btn.disabled = false;
  }
}

function getFallbackData() {
  return {
    club_name: "Wandoor Runners Monsoon 100k challenge 2026",
    target_km: 100.0,
    dates: ["2026-09-04"],
    daily_records: {
      "2026-09-04": [
        { athlete_id: "157557051", name: "Mohamed Shajahan Parancheri", daily_distance_km: 40.43, daily_runs: 4, avg_pace: "6:04", weekly_cumulative_km: 40.43 }
      ]
    },
    athlete_totals: {
      "157557051": { name: "Mohamed Shajahan Parancheri", total_challenge_km: 40.43, pct_completed: 40.4, active_days: 4, current_streak: 4 }
    }
  };
}
