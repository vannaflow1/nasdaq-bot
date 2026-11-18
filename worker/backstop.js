// worker/backstop.js - starts Volta's important GitHub jobs when GitHub's own scheduler skips them.
//
// Why (plain words): GitHub Actions often delays or drops scheduled runs. On 16 Nov 2026 it dropped every
// London-outlook try; on 18 Nov it ran almost nothing from 13:00 UTC on, so a whole US session of option-chain
// snapshots was missing - and the watchdog, which runs on the same scheduler, was silent too.
// Cloudflare runs this every 5 minutes (wrangler.toml [triggers]). For each important job it asks GitHub
// "when did this last start?" and, only if a run is overdue, starts one itself. If GitHub's scheduler is
// working, this does nothing. The jobs guard themselves (post once per day etc.), so an extra run is harmless.
//
// Needs ONE Cloudflare secret, set by the owner in the Cloudflare dashboard: DISPATCH_TOKEN = a fine-grained
// GitHub token for vannaflow1/nasdaq-bot only, permission "Actions: Read and write". Without it this does nothing.
// All times are UTC. Days: 0 = Sunday ... 6 = Saturday. Test: node worker/backstop.test.mjs

const WEEK = [1, 2, 3, 4, 5];
const ALL = [0, 1, 2, 3, 4, 5, 6];

// "every": keep the job alive inside the window - start one if the newest run is older than `gap` minutes.
// "at":    the job's own cron times - start one if a time passed `grace` minutes ago (up to 40 more) and no run started since.
export const RULES = [
  { wf: "trump.yml",       kind: "every", days: ALL,  from: "00:00", to: "24:00", gap: 30 },
  { wf: "watchdog.yml",    kind: "every", days: ALL,  from: "00:00", to: "24:00", gap: 75, inputs: { dry: "no" } },
  { wf: "chain-snap.yml",  kind: "every", days: WEEK, from: "13:00", to: "22:00", gap: 12 },
  { wf: "session.yml",     kind: "every", days: WEEK, from: "12:00", to: "22:00", gap: 40 },
  { wf: "nerd-live.yml",   kind: "every", days: WEEK, from: "13:00", to: "21:00", gap: 40 },
  { wf: "bias.yml",        kind: "every", days: WEEK, from: "13:00", to: "22:00", gap: 30, inputs: { dry: "no" } },
  { wf: "outlook.yml",     kind: "every", days: WEEK, from: "06:00", to: "08:00", gap: 25, inputs: { dry: "no" } },
  { wf: "outlook.yml",     kind: "every", days: WEEK, from: "12:00", to: "14:15", gap: 25, inputs: { dry: "no" } },
  { wf: "morning.yml",     kind: "at", days: WEEK, times: ["12:45", "13:45"] },
  { wf: "volflag.yml",     kind: "at", days: WEEK, times: ["19:37", "20:37"] },
  { wf: "evening.yml",     kind: "at", days: WEEK, times: ["20:40", "21:40"] },
  { wf: "brain-retrain.yml", kind: "at", days: WEEK, times: ["21:50"] },
  { wf: "macro.yml",       kind: "at", days: WEEK, times: ["22:15"] },
  { wf: "bar-archive.yml", kind: "at", days: WEEK, times: ["23:15"] },
  { wf: "families.yml",    kind: "at", days: [2, 3, 4, 5, 6], times: ["06:40"] },
  { wf: "tests.yml",       kind: "at", days: ALL, times: ["04:10"] },
  { wf: "scoreboard.yml",  kind: "at", days: ALL, times: ["09:20"], inputs: { dry: "no" } },
];
const GRACE = 12, LATE_LIMIT = 40;           // "at" rules: act 12-52 minutes after the missed time, never later

const mins = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };

// Which rules could need a run right now (no GitHub calls yet). -> [{rule, since}] where `since` is the time
// (ms) after which a started run counts as proof that the job is alive.
export function candidates(now, rules = RULES) {
  const day = now.getUTCDay(), m = now.getUTCHours() * 60 + now.getUTCMinutes(), out = [];
  const midnight = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  for (const r of rules) {
    if (!r.days.includes(day)) continue;
    if (r.kind === "every") {
      if (m >= mins(r.from) + 5 && m < mins(r.to)) out.push({ rule: r, since: now.getTime() - r.gap * 60000 });
    } else {
      for (const t of r.times) {
        const late = m - mins(t);
        if (late >= GRACE && late < GRACE + LATE_LIMIT) out.push({ rule: r, since: midnight + (mins(t) - 2) * 60000 });
      }
    }
  }
  return out;
}

// Pure decision: given the newest run start time per workflow (ms or null), which workflows to start.
export function decide(now, newest, rules = RULES) {
  const start = new Map();
  for (const { rule, since } of candidates(now, rules)) {
    const t = newest[rule.wf];
    if (t === undefined) continue;                       // could not ask GitHub: do nothing rather than guess
    if (t === null || t < since) start.set(rule.wf, rule.inputs || {});
  }
  return [...start].map(([wf, inputs]) => ({ wf, inputs }));
}

export async function backstop(env, now = new Date()) {
  const tok = String(env.DISPATCH_TOKEN || "").trim();
  if (!tok) { console.log("backstop: DISPATCH_TOKEN not set - doing nothing"); return []; }
  const repo = String(env.REPO || "vannaflow1/nasdaq-bot").replace(/["'\s]/g, "");
  const h = { Authorization: `Bearer ${tok}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
              "User-Agent": "volta-backstop" };
  const newest = {};
  for (const wf of new Set(candidates(now).map((c) => c.rule.wf))) {
    try {
      const r = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${wf}/runs?per_page=1`, { headers: h });
      if (!r.ok) { console.log(`backstop: ${wf} runs -> HTTP ${r.status}`); continue; }
      const run = ((await r.json()).workflow_runs || [])[0];
      newest[wf] = run ? Date.parse(run.created_at) : null;
    } catch (e) { console.log(`backstop: ${wf} ${e}`); }
  }
  const todo = decide(now, newest), done = [];
  for (const { wf, inputs } of todo) {
    const r = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${wf}/dispatches`,
      { method: "POST", headers: { ...h, "Content-Type": "application/json" }, body: JSON.stringify({ ref: "main", inputs }) });
    console.log(`backstop: started ${wf} -> HTTP ${r.status}`);
    if (r.status === 204) done.push(wf);
  }
  return done;
}
