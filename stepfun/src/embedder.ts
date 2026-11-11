import { env, pipeline, type FeatureExtractionPipeline } from "@huggingface/transformers";
import { MODEL_DIR } from "./config";

export type InferenceBackend = "webgpu" | "wasm";
export type ModelPrecision = "fp32" | "fp16" | "int8";

export interface LoadProgress {
  phase: "detect" | "download" | "ready" | "fallback";
  message: string;
  file?: string;
  progress?: number;
}

export class Embedder {
  backend: InferenceBackend = "wasm";
  precision: ModelPrecision = "int8";
  loadMs = 0;
  private pipe: FeatureExtractionPipeline | null = null;
  private initPromise: Promise<void> | null = null;

  get ready(): boolean {
    return this.pipe !== null;
  }

  async init(onProgress: (progress: LoadProgress) => void): Promise<void> {
    if (this.pipe) return;
    if (this.initPromise) return this.initPromise;

    this.initPromise = this._init(onProgress).finally(() => {
      this.initPromise = null;
    });
    return this.initPromise;
  }

  /** Force a precision/backend pair. Used by the quality benchmark, not the main app. */
  async initFixed(
    precision: ModelPrecision,
    backend: InferenceBackend,
    onProgress: (progress: LoadProgress) => void,
  ): Promise<void> {
    if (this.pipe) return;
    const started = performance.now();
    configureEnvironment();
    onProgress({ phase: "download", message: `加载 ${precision.toUpperCase()} 基线模型…` });
    this.pipe = await this.load(precision, backend, onProgress);
    this.backend = backend;
    this.precision = precision;
    this.loadMs = performance.now() - started;
    onProgress({ phase: "ready", message: `${backend} + ${precision} 已就绪` });
  }

  private async _init(onProgress: (progress: LoadProgress) => void): Promise<void> {
    const started = performance.now();
    configureEnvironment();

    onProgress({ phase: "detect", message: "检测浏览器推理后端…" });
    const gpuAvailable = await this.hasWebGpu();

    if (gpuAvailable) {
      try {
        onProgress({ phase: "download", message: "正在加载 FP16 模型（WebGPU）…" });
        this.pipe = await this.load("fp16", "webgpu", onProgress);
        this.backend = "webgpu";
        this.precision = "fp16";
        this.loadMs = performance.now() - started;
        onProgress({ phase: "ready", message: "WebGPU + FP16 已就绪" });
        return;
      } catch (error) {
        console.warn("WebGPU init failed, falling back to WASM", error);
        onProgress({
          phase: "fallback",
          message: `WebGPU 初始化失败，自动降级到 WASM：${shortError(error)}`,
        });
      }
    } else {
      onProgress({ phase: "fallback", message: "当前浏览器不支持 WebGPU，使用 WASM" });
    }

    onProgress({ phase: "download", message: "正在加载 INT8 模型（WASM）…" });
    this.pipe = await this.load("int8", "wasm", onProgress);
    this.backend = "wasm";
    this.precision = "int8";
    this.loadMs = performance.now() - started;
    onProgress({ phase: "ready", message: "WASM + INT8 已就绪" });
  }

  private async load(
    precision: ModelPrecision,
    backend: InferenceBackend,
    onProgress: (progress: LoadProgress) => void,
  ): Promise<FeatureExtractionPipeline> {
    const createPipeline = pipeline as unknown as (
      task: string,
      model: string,
      options: Record<string, unknown>,
    ) => Promise<FeatureExtractionPipeline>;
    return createPipeline("feature-extraction", MODEL_DIR, {
      dtype: precision,
      device: backend,
      progress_callback: (data: Record<string, unknown>) => {
        const status = String(data.status ?? "");
        if (status === "progress") {
          onProgress({
            phase: "download",
            message: `下载模型分片 ${String(data.file ?? "")}`,
            file: String(data.file ?? ""),
            progress: Number(data.progress ?? 0),
          });
        }
      },
    });
  }

  async embed(texts: string[], batchSize = 8): Promise<number[][]> {
    if (!this.pipe) throw new Error("embedding model is not loaded");
    const all: number[][] = [];
    for (let offset = 0; offset < texts.length; offset += batchSize) {
      const batch = texts.slice(offset, offset + batchSize);
      const tensor = await this.pipe(batch, { pooling: "mean", normalize: true });
      const values = (tensor as unknown as { tolist(): number[] | number[][] }).tolist();
      if (Array.isArray(values[0])) {
        all.push(...(values as number[][]));
      } else {
        all.push(values as number[]);
      }
    }
    return all;
  }

  async dispose(): Promise<void> {
    if (!this.pipe) return;
    await this.pipe.dispose();
    this.pipe = null;
  }

  private async hasWebGpu(): Promise<boolean> {
    const gpu = (navigator as Navigator & {
      gpu?: { requestAdapter(): Promise<unknown | null> };
    }).gpu;
    if (!gpu) return false;
    try {
      return (await gpu.requestAdapter()) !== null;
    } catch {
      return false;
    }
  }
}

function shortError(error: unknown): string {
  if (error instanceof Error) return error.message.slice(0, 120);
  return String(error).slice(0, 120);
}

function configureEnvironment(): void {
  env.allowRemoteModels = true;
  env.allowLocalModels = true;
  env.localModelPath = `${import.meta.env.BASE_URL}models/`;
  env.remoteHost = "https://hf-mirror.com";
  env.useBrowserCache = true;
  const wasm = env.backends.onnx?.wasm;
  if (wasm) {
    wasm.wasmPaths = `${import.meta.env.BASE_URL}ort/`;
    wasm.numThreads = 1;
  }
}
