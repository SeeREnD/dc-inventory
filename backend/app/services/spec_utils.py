"""硬件规格的展示摘要与 Excel 单元格编解码。

设计取舍：Excel 的 CPU/显卡/硬盘 列用 JSON 字符串存储，保证导出→导入无损往返；
可读的摘要（spec_summary）只由 App 界面展示，不参与 Excel 解析。
"""

import json

KIND_LABELS = {"cpu": "CPU", "gpu": "显卡", "disk": "硬盘"}


def _num(n) -> str:
    return f"{n:g}" if isinstance(n, (int, float)) else str(n)


def _cap(gb) -> str:
    if not gb:
        return ""
    return f"{gb / 1024:g}T" if gb >= 1024 else f"{gb}G"


def _fmt_cpu(c: dict) -> str:
    head = c.get("model") or ""
    if c.get("sockets"):
        head = f"{c['sockets']}×{head}" if head else f"{c['sockets']}×CPU"
    tail = []
    if c.get("cores_per_cpu"):
        tail.append(f"{c['cores_per_cpu']}C")
    if c.get("freq_ghz"):
        tail.append(f"{_num(c['freq_ghz'])}GHz")
    return " ".join([head] + tail).strip()


def _fmt_gpu(g: dict) -> str:
    head = g.get("model") or ""
    if g.get("count"):
        head = f"{g['count']}×{head}" if head else f"{g['count']}×GPU"
    if g.get("memory_gb"):
        head = f"{head} {g['memory_gb']}G".strip()
    return head


def _fmt_disk(d: dict) -> str:
    head = f"{d['count']}×" if d.get("count") else ""
    head += d.get("type") or "硬盘"
    cap = _cap(d.get("capacity_gb"))
    if cap:
        head += f" {cap}"
    tail = [t for t in (d.get("raid_level"), d.get("role")) if t]
    return " ".join([head] + tail).strip()


def _join(items, fmt) -> str:
    parts = [fmt(i) for i in (items or []) if isinstance(i, dict)]
    return "；".join(p for p in parts if p)


def build_spec_summary(e) -> str | None:
    """生成列表用的一行摘要，如 '2×Intel Xeon 6338 32C 2.0GHz | GPU:4×A100 80G | 8×NVMe 3.84T RAID10'"""
    segments = []
    cpus = _join(getattr(e, "cpus", None), _fmt_cpu)
    gpus = _join(getattr(e, "gpus", None), _fmt_gpu)
    disks = _join(getattr(e, "disks", None), _fmt_disk)
    if cpus:
        segments.append(cpus)
    if gpus:
        segments.append(f"GPU:{gpus}")
    if disks:
        segments.append(disks)
    return " | ".join(segments) if segments else None


def specs_to_cell(items) -> str | None:
    """导出为 Excel 单元格：JSON 字符串（无损）"""
    if not items:
        return None
    return json.dumps(items, ensure_ascii=False)


def cell_to_specs(cell, kind: str) -> tuple[list[dict] | None, str | None]:
    """导入解析：返回 (规格数组 | None, 警告 | None)。

    - 空单元格 → (None, None)，调用方据此判断“不修改”；
    - 合法 JSON 数组/对象 → 结构化；
    - 其他文本 → 宽容地塞进单条的 model/type，并给出警告，绝不静默丢数据。
    """
    if cell in (None, ""):
        return None, None
    text = str(cell).strip()
    if not text:
        return None, None
    try:
        data = json.loads(text)
    except (ValueError, json.JSONDecodeError):
        data = None
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)], None
    if isinstance(data, dict):
        return [data], None

    label = KIND_LABELS.get(kind, kind)
    key = "model" if kind in ("cpu", "gpu") else "type"
    warning = f"{label}列不是 JSON 数组，已按纯文本保存（如需结构化请在界面补全）"
    return [{key: text}], warning
