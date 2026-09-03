/**
 * ⚡ 1-Click Strava Leaderboard Bookmarklet
 * 
 * HOW TO USE:
 * 1. Create a new bookmark in your Chrome browser (Name: "⚡ Sync Leaderboard")
 * 2. In the URL field, paste the minified javascript below (starting with javascript:(function(){...}) )
 * 3. Replace YOUR_WEBHOOK_URL_HERE with your Google Apps Script Webhook URL
 * 4. Whenever you open https://www.strava.com/clubs/2317931/leaderboard, just click this bookmark!
 * 5. It will extract all runners and sync directly to your Google Sheet in 1 second!
 */

javascript:(function(){
  const WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE";
  
  const rows = document.querySelectorAll("div.leaders table tbody tr, table.dense tbody tr, table.leaderboard tbody tr");
  if (!rows || rows.length === 0) {
    alert("Could not find the Strava leaderboard table. Make sure you are on the club leaderboard page!");
    return;
  }
  
  const today = new Date().toISOString().split("T")[0];
  const athletes = [];
  
  rows.forEach(row => {
    const cells = row.querySelectorAll("td, th");
    if (cells.length >= 4) {
      const rank = parseInt(cells[0].innerText.trim()) || 0;
      const name = cells[1].innerText.trim();
      const dist = parseFloat(cells[2].innerText.replace(/[^\d.]/g, "")) || 0;
      const runs = parseInt(cells[3].innerText.replace(/\D/g, "")) || 0;
      const longest = cells.length > 4 ? parseFloat(cells[4].innerText.replace(/[^\d.]/g, "")) || 0 : 0;
      const pace = cells.length > 5 ? cells[5].innerText.trim() : "--";
      const elev = cells.length > 6 ? parseInt(cells[6].innerText.replace(/\D/g, "")) || 0 : 0;
      
      const img = row.querySelector("img");
      const avatar = img ? img.src : "";
      
      if (rank > 0 && name) {
        athletes.push({
          rank: rank,
          athlete_id: name.toLowerCase().replace(/\W+/g, "_"),
          name: name,
          avatar_url: avatar,
          distance_km: dist,
          runs_count: runs,
          longest_km: longest,
          avg_pace: pace,
          elev_gain_m: elev
        });
      }
    }
  });
  
  if (athletes.length === 0) {
    alert("No athletes found in table.");
    return;
  }
  
  if (WEBHOOK_URL === "YOUR_WEBHOOK_URL_HERE" || !WEBHOOK_URL) {
    alert(`Found ${athletes.length} runners! Please configure your Google Sheet Webhook URL in the bookmark code.`);
    console.log("Athletes scraped:", athletes);
    return;
  }
  
  fetch(WEBHOOK_URL, {
    method: "POST",
    mode: "no-cors",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      date: today,
      target_km: 100,
      daily_logs: athletes.map(a => ({
        date: today,
        athlete_id: a.athlete_id,
        name: a.name,
        daily_distance_km: a.distance_km,
        daily_runs: a.runs_count,
        avg_pace: a.avg_pace,
        daily_elev_gain_m: a.elev_gain_m,
        weekly_cumulative_km: a.distance_km
      }))
    })
  }).then(() => {
    alert(`✅ Successfully synced ${athletes.length} runners to your Google Sheet!`);
  }).catch(err => {
    alert("Error syncing: " + err);
  });
})();
