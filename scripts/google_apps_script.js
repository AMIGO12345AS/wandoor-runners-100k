/**
 * Google Apps Script Webhook for Strava Club Day-by-Day Tracker
 * 
 * SETUP INSTRUCTIONS (Takes 1 minute):
 * 1. Open your Google Sheet
 * 2. Click Extensions > Apps Script
 * 3. Delete any existing code and PASTE this entire script
 * 4. Click 'Save' (floppy disk icon)
 * 5. Click 'Deploy' (top right) > 'New deployment'
 * 6. Select type: 'Web app'
 *    - Description: Strava Club Sync
 *    - Execute as: Me
 *    - Who has access: Anyone (or Anyone with the link)
 * 7. Click 'Deploy' and copy the 'Web app URL'
 * 8. Add that URL to your GitHub Secrets as GOOGLE_SHEET_WEBHOOK_URL
 */

function doPost(e) {
  try {
    const contents = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    
    const dailyLogs = contents.daily_logs || [];
    const athleteTotals = contents.athlete_totals || {};
    const dateStr = contents.date || new Date().toISOString().split('T')[0];
    
    // 1. Update Daily_Logs Tab
    updateDailyLogs(ss, dailyLogs, dateStr);
    
    // 2. Update Challenge_Leaderboard Tab
    updateLeaderboard(ss, athleteTotals, contents.target_km || 100);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Sheet updated successfully",
      rows_added: dailyLogs.length
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function updateDailyLogs(ss, dailyLogs, dateStr) {
  let sheet = ss.getSheetByName("Daily_Logs");
  if (!sheet) {
    sheet = ss.insertSheet("Daily_Logs");
    const header = [
      "Date", "Athlete ID", "Athlete Name", "Today Distance (km)", 
      "Today Runs", "Avg Pace", "Elevation (m)", "Week Cumulative (km)"
    ];
    sheet.appendRow(header);
    sheet.getRange(1, 1, 1, header.length).setFontWeight("bold").setBackground("#FC4C02").setFontColor("#FFFFFF");
    sheet.setFrozenRows(1);
  }
  
  // Format and append rows for athletes with runs today
  const rows = [];
  dailyLogs.forEach(log => {
    rows.push([
      log.date,
      log.athlete_id,
      log.name,
      log.daily_distance_km,
      log.daily_runs,
      log.avg_pace,
      log.daily_elev_gain_m,
      log.weekly_cumulative_km
    ]);
  });
  
  if (rows.length > 0) {
    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  }
}

function updateLeaderboard(ss, athleteTotals, targetKm) {
  let sheet = ss.getSheetByName("Challenge_Leaderboard");
  if (!sheet) {
    sheet = ss.insertSheet("Challenge_Leaderboard");
  }
  
  sheet.clearContents();
  const header = [
    "Rank", "Athlete Name", "Total Completed (km)", "Target (km)", 
    "% Completed", "Remaining (km)", "Active Days", "Current Streak", "Status"
  ];
  sheet.appendRow(header);
  sheet.getRange(1, 1, 1, header.length).setFontWeight("bold").setBackground("#20232A").setFontColor("#FFFFFF");
  sheet.setFrozenRows(1);
  
  const athletes = Object.values(athleteTotals);
  athletes.sort((a, b) => b.total_challenge_km - a.total_challenge_km);
  
  const rows = [];
  athletes.forEach((a, idx) => {
    const isFinisher = a.total_challenge_km >= targetKm;
    const status = isFinisher ? "🏆 FINISHER" : (a.pct_completed >= 50 ? "⚡ On Track" : "🏃 Moving");
    rows.push([
      idx + 1,
      a.name,
      a.total_challenge_km,
      targetKm,
      a.pct_completed + "%",
      a.remaining_km,
      a.active_days,
      a.current_streak,
      status
    ]);
  });
  
  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, rows[0].length).setValues(rows);
  }
}
