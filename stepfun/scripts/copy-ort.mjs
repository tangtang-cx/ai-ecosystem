/** Copy the ONNX Runtime Web runtime into public/ort for offline WASM/WebGPU use. */
import { copyFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const source = fileURLToPath(new URL("../node_modules/onnxruntime-web/dist/", import.meta.url));
const target = fileURLToPath(new URL("../public/ort/", import.meta.url));

const names = [
  "ort-wasm-simd-threaded.jsep.wasm",
  "ort-wasm-simd-threaded.jsep.mjs",
  "ort-wasm-simd-threaded.wasm",
  "ort-wasm-simd-threaded.mjs",
];

await mkdir(target, { recursive: true });
for (const name of names) {
  await copyFile(join(source, name), join(target, name));
}
console.log(`copied ${names.length} ONNX Runtime Web files to public/ort`);
