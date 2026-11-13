"""Simulate a judge machine that only has the core dependency installed.

Blocks onnxruntime / tokenizers / pylibseekdb at import time and checks that
the project still imports and still runs.
"""

import builtins
import sys

BLOCKED = {"pylibseekdb", "onnxruntime", "tokenizers"}
real_import = builtins.__import__


def guard(name, *args, **kwargs):
    if name.split(".")[0] in BLOCKED:
        raise ImportError(f"No module named {name!r} (simulated clean env)")
    return real_import(name, *args, **kwargs)


builtins.__import__ = guard

SAMPLE = "SELECT * FROM t WHERE DATE(c)='2026-01-01' LIMIT 20, 200000;"

for target in ("qoder", "Dify"):
    print(f"--- {target} ---")
    sys.path.insert(0, target)
    if target == "qoder":
        import reviewer
        import seekdb_bridge

        ids = sorted({item.id for item in reviewer.analyze(SAMPLE)})
        print("  imports OK; rules fired:", ids)
        print("  seekdb optional ->", seekdb_bridge.health("http://127.0.0.1:8901"))
    else:
        import embedder
        import seekdb_store
        import auto_start

        instance = embedder.Embedder.get()
        vector = instance.embed_one(SAMPLE)
        norm = sum(value * value for value in vector) ** 0.5
        print("  imports OK; embedder mode:", "fallback" if instance.is_fallback else "bge")
        print("  vector dim:", len(vector), "norm:", round(norm, 6))
        print("  service start (fresh port) ->", auto_start.ensure_service("http://127.0.0.1:8901", wait=10))

print("\nCLEAN-ENV CHECK DONE: every project imports and runs without the optional deps")
