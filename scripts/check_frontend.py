"""前端页面功能点分析 - 抓取 HTML 和 JS 关键字"""
import json, re, urllib.request

BASE = "http://127.0.0.1:8001"

def fetch(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.read().decode("utf-8", errors="replace")

idx = fetch("/static/index.html")
login = fetch("/static/login.html")
app = fetch("/static/js/app.js")

print("=" * 70)
print("前端静态分析")
print("=" * 70)

print("\n[登录页 login.html] 主要元素")
for m in re.finditer(r'<(\w+)[^>]*?(?:id|placeholder|name|type)="([^"]+)"[^>]*>', login):
    if m.group(1) in ("input", "button", "form", "select"):
        print(f"  {m.group(1):7s} name/id={m.group(2)}")

print("\n[主界面 index.html] 主要区块")
for m in re.finditer(r'<(\w+)[^>]*?(?:id|class)="([^"]+)"', idx):
    if "tab" in m.group(2).lower() or "section" in m.group(2).lower() or "menu" in m.group(2).lower():
        print(f"  {m.group(1):7s} id/class={m.group(2)}")

print("\n[app.js] 后端 API 调用")
api_calls = set(re.findall(r'["\']/api/[^"\']+["\']', app))
for a in sorted(api_calls):
    print(f"  {a}")
print(f"  共 {len(api_calls)} 个 API 调用")

print("\n[app.js] 注册事件")
for m in re.finditer(r'(?:addEventListener|on\w+)\(["\']([^"\']+)["\']', app):
    print(f"  {m.group(1)}")

print("\n[app.js] 关键函数")
for m in re.finditer(r'function\s+(\w+)\s*\(', app):
    print(f"  {m.group(1)}()")