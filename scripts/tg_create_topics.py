"""一次性管理工具：用 Bot API 在共学群里批量创建 Topics。
Bot 需要是群管理员且有 Manage Topics 权限（已配置）。
token 从 ~/.hermes/.env 读取，不接受命令行传入，避免进入 shell 历史。
"""
import json
import os
import urllib.request
# ---
proxy = "http://127.0.0.1:7890"
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": proxy, "https": proxy})
)
# ---
token = None
with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
# ---
CHAT_ID = "-1004357682219"
TOPICS = ["套利学习", "策略研究", "数据与回测", "开发", "打卡"]
# ---
def call(method, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with opener.open(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())
# ---
for name in TOPICS:
    res = call("createForumTopic", chat_id=CHAT_ID, name=name)
    if res.get("ok"):
        t = res["result"]
        print(f"OK  {name} -> thread_id {t['message_thread_id']}")
    else:
        print(f"ERR {name}: {res.get('description')}")
