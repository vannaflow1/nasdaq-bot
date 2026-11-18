// node worker/backstop.test.mjs  - checks the backstop's decisions without touching GitHub.
import assert from "node:assert/strict";
import { decide, candidates, backstop } from "./backstop.js";

const at = (iso) => new Date(iso + "Z");
const ago = (now, min) => now.getTime() - min * 60000;
const names = (todo) => todo.map((t) => t.wf).sort();

// Wed 18 Nov 2026 16:50 UTC - what really happened: nothing of the session ran since 13:00.
let now = at("2026-11-18T16:50:00");
let newest = { "trump.yml": ago(now, 228), "watchdog.yml": ago(now, 532), "chain-snap.yml": ago(now, 1000),
               "session.yml": ago(now, 1000), "nerd-live.yml": ago(now, 1000), "bias.yml": ago(now, 1000) };
assert.deepEqual(names(decide(now, newest)), ["bias.yml", "chain-snap.yml", "nerd-live.yml", "session.yml", "trump.yml", "watchdog.yml"]);
assert.deepEqual(decide(now, newest).find((t) => t.wf === "bias.yml").inputs, { dry: "no" });

// Same moment, GitHub working normally: nothing to do.
newest = { "trump.yml": ago(now, 6), "watchdog.yml": ago(now, 3), "chain-snap.yml": ago(now, 4),
           "session.yml": ago(now, 17), "nerd-live.yml": ago(now, 15), "bias.yml": ago(now, 6) };
assert.deepEqual(decide(now, newest), []);

// Could not ask GitHub about a job (undefined): never start it blindly.
assert.deepEqual(names(decide(now, { "trump.yml": ago(now, 300) })), ["trump.yml"]);

// Weekend: no session jobs, ever.
now = at("2026-11-21T16:50:00");
assert.ok(!candidates(now).some((c) => ["chain-snap.yml", "session.yml", "bias.yml", "outlook.yml"].includes(c.rule.wf)));

// London outlook: Monday 16 Nov, GitHub dropped every try -> started at 06:05 UTC at the latest by 06:30.
now = at("2026-11-16T06:30:00");
assert.deepEqual(names(decide(now, { "trump.yml": ago(now, 5), "watchdog.yml": ago(now, 5), "outlook.yml": ago(now, 3000) })), ["outlook.yml"]);

// "at" jobs: evening at 20:40 missed -> started between 20:52 and 21:32, not before, not after, not twice.
const ev = (iso, t) => decide(at(iso), { "evening.yml": t, "trump.yml": Date.now() * 2, "watchdog.yml": Date.now() * 2,
  "chain-snap.yml": Date.now() * 2, "session.yml": Date.now() * 2, "bias.yml": Date.now() * 2, "volflag.yml": Date.now() * 2 })
  .some((x) => x.wf === "evening.yml");
const yesterday = Date.parse("2026-11-17T21:40:00Z");
assert.equal(ev("2026-11-18T20:50:00", yesterday), false);                        // still within grace
assert.equal(ev("2026-11-18T20:55:00", yesterday), true);                         // missed -> start
assert.equal(ev("2026-11-18T20:55:00", Date.parse("2026-11-18T20:44:00Z")), false); // GitHub ran it (late) -> nothing
assert.equal(ev("2026-11-18T21:35:00", yesterday), false);                        // too late, wait for the 21:40 try

// No token -> nothing happens and no network call is made.
const realFetch = globalThis.fetch; let calls = 0; globalThis.fetch = async () => { calls++; };
assert.deepEqual(await backstop({}, at("2026-11-18T16:50:00")), []); assert.equal(calls, 0);

// With a token: asks GitHub, starts only what is overdue, sends the inputs.
const posted = [];
globalThis.fetch = async (url, opt = {}) => {
  if (opt.method === "POST") { posted.push([url.split("/workflows/")[1], JSON.parse(opt.body)]); return { status: 204 }; }
  const wf = url.split("/workflows/")[1].split("/")[0];
  const t = wf === "bias.yml" ? "2026-11-18T12:00:00Z" : "2026-11-18T16:47:00Z";
  return { ok: true, json: async () => ({ workflow_runs: [{ created_at: t }] }) };
};
const done = await backstop({ DISPATCH_TOKEN: "x" }, at("2026-11-18T16:50:00"));
assert.deepEqual(done, ["bias.yml"]);
assert.deepEqual(posted, [["bias.yml/dispatches", { ref: "main", inputs: { dry: "no" } }]]);
globalThis.fetch = realFetch;
console.log("backstop tests OK");
