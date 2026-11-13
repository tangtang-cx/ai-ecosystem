from pathlib import Path

t = Path("Dify/app.yml").read_text(encoding="utf-8")
block = t.split("file_upload:")[1][:600]
print("file_upload enabled:", "enabled: true" in block)
print("provider empty:", "provider: ''" in t)
print("model hint in description:", "导入后必做一步" in t)

t2 = Path("Dify/app-with-model.yml").read_text(encoding="utf-8")
print("variant model set:", "provider: tongyi" in t2 and "name: qwen-plus" in t2)
print("variant file_upload enabled:", "enabled: true" in t2.split("file_upload:")[1][:600])
