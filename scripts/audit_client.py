"""分析客户端 (PyQt) 调用了哪些接口"""
import os, re
CLIENT_DIR = r"c:/wzt_WorkFile/project/customer-insurance-work-system/client"

api_calls = set()
for root, _, files in os.walk(CLIENT_DIR):
    if "dist" in root:
        continue
    for f in files:
        if not f.endswith(".py"):
            continue
        p = os.path.join(root, f)
        with open(p, "r", encoding="utf-8", errors="ignore") as fh:
            src = fh.read()
        # 模板字符串中的路径
        for m in re.finditer(r"/api/[a-zA-Z_/\${}]+", src):
            api_calls.add((f, m.group(0)))
        # 引号中的
        for m in re.finditer(r"['\"](/api/[^'\"]+)['\"]", src):
            api_calls.add((f, m.group(1)))

for f, url in sorted(api_calls):
    print(f"{f:30s} {url}")
print(f"\n客户端共 {len(api_calls)} 处 API 调用")
print()

# UI 功能点
print("\n[client/ui 功能模块]")
for root, _, files in os.walk(CLIENT_DIR):
    if "dist" in root:
        continue
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                src = fh.read()
            classes = re.findall(r"class\s+(\w+)", src)
            methods = re.findall(r"def\s+(?!__)(\w+)\(", src)
            if classes or methods:
                rel = os.path.relpath(p, CLIENT_DIR)
                print(f"  {rel}")
                for cls in classes:
                    print(f"    class {cls}")
                for m in methods[:8]:
                    print(f"      .{m}()")
                if len(methods) > 8:
                    print(f"      ... ({len(methods) - 8} more)")