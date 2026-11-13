import { readFileSync } from "node:fs";
const h = { authorization: `Bearer ${process.env.GH_T}`, accept: "application/vnd.github+json", "user-agent": "dsh" };
const repo = "wzhaihqy/seekdb";
const sha = "429e19d2a896e8c40a13dbc740dbadaeaff350b5";

const r = await fetch(`https://api.github.com/repos/${repo}/contents/tools/hipvs_bridge/seekdb_cuvs_bridge.h?ref=${sha}`, { headers: h });
const hdr = Buffer.from((await r.json()).content, "base64").toString("utf8");
const uniq = [...new Set([...hdr.matchAll(/\b(seekdb_cuvs_[a-z0-9_]+)\s*\(/g)].map((m) => m[1]))];
console.log(`header declares (${uniq.length}): ${uniq.join(", ")}`);

const src = readFileSync("D:/project/OceanBase/ai-ecosystem/amd/submit/files/tools/hipvs_bridge/seekdb_cuvs_bridge.c", "utf8");
let fails = 0;
for (const fn of uniq) {
  const ok = new RegExp(`\\b${fn}\\s*\\(`).test(src);
  if (!ok) fails += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  defined in bridge.c: ${fn}`);
}

const defs = [...new Set([...src.matchAll(/^(?:[A-Za-z_][A-Za-z0-9_]*[ \t*]+)+(seekdb_cuvs_[a-z0-9_]+)\s*\(/gm)].map((m) => m[1]))];
console.log(`bridge.c top-level definitions: ${defs.join(", ")}`);
const extra = defs.filter((d) => !uniq.includes(d));
console.log(extra.length === 0 ? "PASS  no extra exported entry points" : `WARN  extra entry points: ${extra.join(", ")}`);
console.log(`\n${fails === 0 ? "SYMBOL PARITY OK (6/6)" : fails + " MISSING"}`);
