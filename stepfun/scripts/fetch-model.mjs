/**
 * Fetch the pinned embedding model from a Hugging Face mirror.
 *
 * Usage:
 *   node scripts/fetch-model.mjs            # INT8 only (default, committed)
 *   node scripts/fetch-model.mjs --fp32     # also fetch FP32 for quality comparison
 *   node scripts/fetch-model.mjs --fp16     # also fetch FP16
 */
import { mkdir, stat, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = "Xenova/bge-small-zh-v1.5";
const REVISION = "75c43b069aac4d136ba6bc1122f995fedcfd2781";
const HOST = process.env.MODEL_HOST || "https://hf-mirror.com";
const ROOT = new URL("../public/models/bge-small-zh-v1.5/", import.meta.url);
const ROOT_DIR = fileURLToPath(ROOT);

const files = [
  "config.json",
  "tokenizer.json",
  "tokenizer_config.json",
  "special_tokens_map.json",
  "onnx/model_int8.onnx",
];

if (process.argv.includes("--fp32")) files.push("onnx/model.onnx");
if (process.argv.includes("--fp16")) files.push("onnx/model_fp16.onnx");
if (process.argv.includes("--all")) {
  for (const name of ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"]) {
    if (!files.includes(name)) files.push(name);
  }
}

async function download(relative) {
  const target = join(ROOT_DIR, relative);
  try {
    const info = await stat(target);
    if (info.size > 0) {
      console.log(`skip  ${relative} (${info.size} bytes)`);
      return;
    }
  } catch {
    // Missing: download it.
  }
  const url = `${HOST}/${REPO}/resolve/${REVISION}/${relative}`;
  console.log(`fetch ${relative}`);
  const response = await fetch(url, { redirect: "follow" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, bytes);
  console.log(`saved ${relative} (${bytes.length} bytes)`);
}

for (const file of files) await download(file);
console.log("model ready:", ROOT_DIR);
