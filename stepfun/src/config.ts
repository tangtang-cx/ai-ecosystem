export const MODEL_ID = "Xenova/bge-small-zh-v1.5";
export const MODEL_DIR = "bge-small-zh-v1.5";
export const EMBEDDING_DIM = 512;
export const COLLECTION_NAME = "browser_knowledge_base";

export const MODEL_SIZES = {
  fp32: 94_851_877,
  fp16: 47_497_427,
  int8: 23_903_394,
} as const;

export type Precision = keyof typeof MODEL_SIZES;

export function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

export function compressionRatio(from: number, to: number): string {
  return `${(from / to).toFixed(2)}x`;
}
