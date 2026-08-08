#!/usr/bin/env python3
"""Jupiter 协议清单哨兵：发现新上/下线的协议。

数据源：https://api.jup.ag/swap/v1/program-id-to-label（2026-08-07 实测可用）
逻辑：拉最新清单 → 与上次快照对比 → 新协议（上线）/消失协议（下线/弃用）→ 输出
watchdog 模式：有变化才输出。

用法：
  python3 protocol_sentinel.py            # 首次：建快照，静默
  python3 protocol_sentinel.py --quiet    # cron 模式：有变化才输出
"""

import json
import os
import subprocess
import sys
import datetime

SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "jup_protocols_snapshot.json")
SNAPSHOT = os.path.normpath(SNAPSHOT)
API_URL = "https://api.jup.ag/swap/v1/program-id-to-label"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")


def fetch_labels():
    cmd = ["curl", "-skL", "--max-time", "30", "-x", PROXY, "-H", "User-Agent: Mozilla/5.0", API_URL]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if not r.stdout.strip().startswith("{"):
        raise RuntimeError(f"API 返回异常: {r.stdout[:100]}")
    return json.loads(r.stdout)


def main():
    quiet = "--quiet" in sys.argv
    labels = fetch_labels()
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if not os.path.exists(SNAPSHOT):
        os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
        with open(SNAPSHOT, "w") as f:
            json.dump({"fetched_at": now, "labels": labels}, f, ensure_ascii=False, indent=1)
        if not quiet:
            print(f"[协议哨兵] 首跑：已建快照（{len(labels)} 个协议），下次开始对比。")
        return

    with open(SNAPSHOT) as f:
        old = json.load(f)
    old_labels = old.get("labels", {})
    old_names = set(old_labels.values())
    new_names = set(labels.values())

    new_protos = sorted(name for name in new_names - old_names)  # 新上线
    gone_protos = sorted(name for name in old_names - new_names)  # 下线/弃用
    renamed = []
    for pid, name in labels.items():
        if pid in old_labels and old_labels[pid] != name:
            renamed.append(f"{old_labels[pid]} → {name}")

    # 更新快照
    with open(SNAPSHOT, "w") as f:
        json.dump({"fetched_at": now, "labels": labels}, f, ensure_ascii=False, indent=1)

    if not new_protos and not gone_protos and not renamed:
        if not quiet:
            print(f"[协议哨兵] {now}：无变化（{len(labels)} 个协议）。")
        return

    lines = [f"🛰️ 协议清单变化（{now}，共 {len(labels)} 个）"]
    if new_protos:
        lines.append(f"\n🆕 新上线（{len(new_protos)}）：")
        lines.extend(f"  • {n}" for n in new_protos)
    if gone_protos:
        lines.append(f"\n💀 下线/弃用（{len(gone_protos)}）：")
        lines.extend(f"  • {n}" for n in gone_protos)
    if renamed:
        lines.append(f"\n🔄 更名（{len(renamed)}）：")
        lines.extend(f"  • {r}" for r in renamed)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
