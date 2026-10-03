"""轻量幂等迁移。

项目未引入 Alembic，`Base.metadata.create_all` 只会在建库时创建缺失的表，
不会为已存在的表补列，所以这里用 SQLite 的 ALTER TABLE 手动同步结构。

兼容两种情形：
- 全新库：create_all 已按最新模型建表 → 此处全部命中、无需改动；
- 存量库：表仍为旧结构 → 重命名 `ip` 并补齐新列。

注意：新增列必须可空且无 server default，否则 SQLite 的 ADD COLUMN 会报错。
"""

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

# 需要补齐的列：列名 -> SQLite DDL 类型（JSON 与 create_all 生成的类型保持一致）
_NEW_COLUMNS = {
    "ip_inband_v6": "VARCHAR(50)",
    "ip_outband_v4": "VARCHAR(50)",
    "ip_outband_v6": "VARCHAR(50)",
    "cpus": "JSON",
    "gpus": "JSON",
    "disks": "JSON",
}


def run_migrations(engine: Engine) -> None:
    insp = inspect(engine)
    if "equipment" not in insp.get_table_names():
        # 全新库，create_all 已是最终结构
        return

    cols = {c["name"] for c in insp.get_columns("equipment")}

    with engine.begin() as conn:
        # a) 旧列 ip 重命名为 ip_inband_v4（SQLite >= 3.25，Python 3.12 自带）
        if "ip" in cols and "ip_inband_v4" not in cols:
            conn.exec_driver_sql("ALTER TABLE equipment RENAME COLUMN ip TO ip_inband_v4")
            cols.discard("ip")
            cols.add("ip_inband_v4")
        elif "ip" in cols and "ip_inband_v4" in cols:
            # b) 半迁移兜底：两列并存时把旧数据补齐，保留旧列（ORM 用显式列名，多一列无害）
            conn.exec_driver_sql(
                "UPDATE equipment SET ip_inband_v4 = ip WHERE ip_inband_v4 IS NULL"
            )

        # c) 补齐缺失的新列
        for name, ddl in _NEW_COLUMNS.items():
            if name not in cols:
                conn.exec_driver_sql(
                    f"ALTER TABLE equipment ADD COLUMN {name} {ddl}"
                )
