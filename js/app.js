/**
 * Wandoor Runners Dashboard Logic
 * Modern, Athletic, Clean Typography, Zero Emojis.
 */

let clubData = null;
let currentTab = "daily"; // "daily" | "overall"
let selectedDate = null;
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
}

function setupEventListeners() {
  const tabDaily = document.getElementById("tabDaily");
  const tabOverall = document.getElementById("tabOverall");
  const dateFilterWrap = document.getElementById("dateFilterWrap");

  tabDaily.addEventListener("click", () => {
    tabDaily.classList.add("active");
    tabOverall.classList.remove("active");
    currentTab = "daily";
    dateFilterWrap.style.display = "flex";
    renderDashboard();
  });

  tabOverall.addEventListener("click", () => {
    tabOverall.classList.add("active");
    tabDaily.classList.remove("active");
    currentTab = "overall";
    dateFilterWrap.style.display = "none";
    renderDashboard();
  });

  document.getElementById("dateSelect").addEventListener("change", (e) => {
    selectedDate = e.target.value;
    renderDashboard();
  });

  document.getElementById("searchInput").addEventListener("input", (e) => {
    searchQuery = e.target.value.toLowerCase().trim();
    renderTable();
  });

  // WhatsApp modal
  const waModal = document.getElementById("whatsappModal");
  document.getElementById("btnOpenWhatsApp").addEventListener("click", () => {
    generateWhatsAppMessage();
    waModal.classList.add("open");
  });
  document.getElementById("waCloseBtn").addEventListener("click", () => waModal.classList.remove("open"));
  waModal.addEventListener("click", (e) => {
    if (e.target.id === "whatsappModal") waModal.classList.remove("open");
  });

  document.getElementById("btnCopyWhatsApp").addEventListener("click", copyWhatsAppText);

  // Athlete modal
  const athleteModal = document.getElementById("athleteModal");
  document.getElementById("modalCloseBtn").addEventListener("click", () => athleteModal.classList.remove("open"));
  athleteModal.addEventListener("click", (e) => {
    if (e.target.id === "athleteModal") athleteModal.classList.remove("open");
  });
}

function renderDashboard() {
  populateDateDropdown();
  renderKPIs();
  renderPodium();
  renderTable();
}

function getLocalISTDateStr() {
  // Always get exact calendar date in Indian Standard Time (Asia/Kolkata)
  try {
    return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
  } catch (e) {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  }
}

function populateDateDropdown() {
  const dateSelect = document.getElementById("dateSelect");
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

function renderKPIs() {
  const athleteTotals = clubData.athlete_totals || {};
  const athletes = Object.values(athleteTotals);
  const dailyLogs = (clubData.daily_records && clubData.daily_records[selectedDate]) || [];

  // Active Runners
  document.getElementById("kpiRunnersCount").textContent = athletes.length;

  // Club Mileage Today
  const totalDist = dailyLogs.reduce((sum, l) => sum + (l.daily_distance_km || 0), 0);
  const activeCount = dailyLogs.filter(l => l.daily_distance_km > 0).length;
  document.getElementById("kpiTodayDistance").innerHTML = `${totalDist.toFixed(1)} <span class="unit">km</span>`;
  document.getElementById("kpiTodayCount").textContent = `${activeCount} runners logged`;

  // Finishers Count (>= 100km)
  const targetKm = clubData.target_km || 100.0;
  const finishers = athletes.filter(a => (a.total_challenge_km || 0) >= targetKm);
  document.getElementById("kpiFinishersCount").textContent = finishers.length;
}

function renderPodium() {
  const grid = document.getElementById("podiumGrid");
  if (!grid) return;
  grid.innerHTML = "";

  const athletes = Object.values(clubData.athlete_totals || {});
  athletes.sort((a, b) => b.total_challenge_km - a.total_challenge_km);

  if (athletes.length < 3) return;

  const top1 = athletes[0];
  const top2 = athletes[1];
  const top3 = athletes[2];

  // Olympic podium order: [Rank 2, Rank 1, Rank 3]
  const podiumOrder = [
    { athlete: top2, rank: 2, badgeClass: "rank-silver", label: "2nd Place" },
    { athlete: top1, rank: 1, badgeClass: "rank-gold", label: "Leading Challenge" },
    { athlete: top3, rank: 3, badgeClass: "rank-bronze", label: "3rd Place" }
  ];

  podiumOrder.forEach(item => {
    const a = item.athlete;
    const cleanName = cleanAthleteName(a.name);
    const card = document.createElement("div");
    card.className = `podium-card ${item.badgeClass}`;
    card.innerHTML = `
      <div class="podium-badge">${item.rank}</div>
      <img src="${a.avatar_url || 'https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'}" 
           onerror="this.src='https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png'" 
           class="podium-avatar" alt="">
      <div class="podium-name" title="${cleanName}">${cleanName}</div>
      <div class="podium-km">${a.total_challenge_km.toFixed(1)} <span style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">km</span></div>
      <div class="podium-pct">${a.pct_completed || 0}% of 100k</div>
    `;
    card.addEventListener("click", () => openAthleteModal(a.athlete_id));
    grid.appendChild(card);
  });
}

function renderTable() {
  const thead = document.getElementById("tableHeaderRow");
  const tbody = document.getElementById("tableBody");
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
        <td class="col-hide-mobile" style="text-align: center;">${r.daily_runs || 1}</td>
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
  document.getElementById("modalStreak").textContent = `${athlete.active_days || 0} active days`;

  const tbody = document.getElementById("modalHistoryTbody");
  tbody.innerHTML = "";
  const barChart = document.getElementById("modalBarChart");
  barChart.innerHTML = "";

  const dates = clubData.dates || [];
  const userLogs = [];

  dates.forEach(d => {
    const logs = clubData.daily_records[d] || [];
    const log = logs.find(l => l.athlete_id === athleteId);
    if (log && log.daily_distance_km > 0) {
      userLogs.push(log);
    }
  });

  if (userLogs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 14px;">No individual runs logged yet.</td></tr>`;
    barChart.innerHTML = `<span style="font-size: 11.5px; color: var(--text-muted); margin: auto;">No activity recorded yet</span>`;
  } else {
    // Render clean athletic vector bars
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

    // Populate history rows
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
  const today = selectedDate || new Date().toISOString().split("T")[0];
  const dailyLogs = (clubData.daily_records && clubData.daily_records[today]) || [];
  const topRunners = [...dailyLogs].filter(l => l.daily_distance_km > 0).slice(0, 5);
  const totalKmToday = dailyLogs.reduce((sum, l) => sum + (l.daily_distance_km || 0), 0);

  let msg = `*WANDOOR RUNNERS - MONSOON 100K CHALLENGE*\n`;
  msg += `Date: ${today}\n\n`;
  msg += `*Top Performers:*\n`;

  if (topRunners.length === 0) {
    msg += `No runs logged for today yet.\n`;
  } else {
    topRunners.forEach((r, idx) => {
      const cleanName = cleanAthleteName(r.name);
      msg += `${idx + 1}. *${cleanName}* - ${r.daily_distance_km.toFixed(1)} km (Pace: ${r.avg_pace || '--'}/km)\n`;
    });
  }

  msg += `\n*Club Total Today:* ${totalKmToday.toFixed(1)} km\n`;
  msg += `Challenge Target: 100 km\n`;

  document.getElementById("whatsappText").value = msg;
}

function copyWhatsAppText() {
  const ta = document.getElementById("whatsappText");
  ta.select();
  document.execCommand("copy");

  const btn = document.getElementById("btnCopyWhatsApp");
  const orig = btn.innerHTML;
  btn.innerHTML = "Copied!";
  setTimeout(() => {
    btn.innerHTML = orig;
  }, 2000);
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
