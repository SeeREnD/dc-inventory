# 数据中心资产管理系统（DCAM）— 运维文档

> 项目代号：DCAM（Data Center Asset Management）；代码目录：`dc-inventory`
> 适用环境：Ubuntu 24.04 / Docker 29 / Docker Compose v5
> 项目路径：`/home/jiwi/projects/dc-inventory/`
> **当前生产运行方式：Docker Compose**（裸机方式保留作备用，见附录）

---

## 1. 架构说明（服务是怎么跑起来的）

系统打包为 **两个 Docker 容器**，由 `docker-compose.yml` 编排：

```
同事浏览器
    │
    │  http://192.168.30.5:5173
    ▼
┌─────────────────────────────┐       ┌──────────────────────────────┐
│ frontend 容器                │ /api/ │ backend 容器                  │
│ nginx:alpine                 │ ────► │ python:3.12-slim + uvicorn   │
│ 提供 Vue 静态页面             │ 内部  │ FastAPI，端口 8000（仅容器网络）│
│ 端口 5173 → 映射到容器 80     │ 网络  │                               │
└─────────────────────────────┘       └──────────────┬───────────────┘
                                                     │
                                        data/dc_inventory.db
                                        (挂载到宿主机，SQLite)
```

- **frontend 容器**：nginx 托管 Vue 构建出来的静态文件；浏览器发出的 `/api` 请求由 nginx 反向代理到 backend 容器。**防火墙只需放行 5173**。
- **backend 容器**：FastAPI 应用，提供 JWT 登录、设备增删改查、Excel 导入导出、统计接口。
- **数据库**：SQLite 单文件，挂载在宿主机 `data/dc_inventory.db`。容器删掉数据也不丢；首次启动自动建表并创建默认账号 `admin / admin123`。
- **自愈能力**：compose 配置了 `restart: unless-stopped` 和后端健康检查（`/api/health`），进程崩溃会自动拉起。

## 2. 目录结构

```
dc-inventory/
├── docker-compose.yml          # 编排文件（镜像源、端口、数据挂载都在这里改）
├── data/
│   └── dc_inventory.db         # ★ 全部业务数据（备份这个文件）
├── backend/
│   ├── Dockerfile              # 后端镜像（ARG REGISTRY 支持国内镜像源）
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # 后端入口（建库、默认 admin）
│       ├── models.py           # 数据表定义
│       ├── auth.py             # JWT 密钥 SECRET_KEY 在这里，正式使用前建议改
│       └── routers/            # users/rooms/equipment/changes/stats/excel
└── frontend/
    ├── Dockerfile              # 两阶段：node 构建 → nginx 托管
    ├── nginx.conf              # 静态托管 + /api 反代规则
    ├── vite.config.js          # 开发模式用（生产由 nginx 承担）
    └── src/                    # 页面源码
```

## 3. 日常操作

```bash
cd ~/projects/dc-inventory

docker compose up -d           # 启动（首次自动构建，约 5 分钟）
docker compose down            # 停止（数据在 ./data/，不会丢）
docker compose restart         # 重启
docker compose ps              # 状态：backend 应为 Up (healthy)
docker compose logs -f         # 实时日志（Ctrl+C 退出，不影响服务）
docker compose logs backend    # 只看后端最近日志
docker compose up -d --build   # 改了代码后重建镜像并启动
```

⚠️ **docker 权限**：本机账号加过 docker 组，但旧会话可能不生效。提示 `permission denied` 时，命令前套一层：`sg docker -c "docker compose ps"`（或退出重新登录一次）。

⚠️ 基础镜像走国内源 `docker.m.daocloud.io`（写在 compose 的 build args）。哪天能直连 Docker Hub 了，把 compose 里两处 `REGISTRY` 改回 `docker.io/library` 即可。

**开机自启**：`restart: unless-stopped` 已配置，服务器重启后 Docker 会自动拉起服务，无需手动操作。如开机 Docker 本身没启动：`sudo systemctl enable --now docker`。

## 4. 端口与防火墙

| 端口 | 归属 | 对外放行 | 说明 |
|---|---|---|---|
| 5173 | frontend 容器 | **是** | 唯一需要放行的端口 |
| 8000 | backend 容器 | 否 | 仅 docker 内部网络可达，宿主机也访问不到 |

防火墙为 ufw，当前规则（只对内网网段放行）：

```bash
sudo ufw status                        # 查看规则
sudo ufw allow from 192.168.30.0/24 to any port 5173 proto tcp comment 'allow dc-inventory 5173'
sudo ufw reload                        # 修改后重载
sudo ufw delete allow from 192.168.30.0/24 to any port 5173 proto tcp   # 撤销
```

## 5. 数据备份与恢复

系统内置备份管理（admin 登录 → 备份管理页）：

- **每日自动备份**：数据库每天自动快照一次到 `data/backups/`
- **保留天数可配置**：备份管理页顶部设置（默认 7 天，超期自动清理）
- **手动备份**：点击"立即创建备份"
- **回退**：选任意备份点"回退到此版本"——系统会先把当前数据自动存为安全快照（"回退前自动"），再恢复所选版本，可反悔
- **下载旧版**：任意备份可下载为 .db 文件（完整数据库快照）

备份文件位置：`~/projects/dc-inventory/data/backups/`（已随 data 目录持久化到宿主机）

命令行手动备份（不登录页面时）：

```bash
mkdir -p ~/backup
cp ~/projects/dc-inventory/data/dc_inventory.db ~/backup/dc_inventory_$(date +%F).db
```

## 5.1 审计日志

admin 登录 → 系统日志页：记录所有**登录成功/失败（含 IP）、退出、改密、用户管理、备份/回退**操作，支持按用户名和操作类型筛选。设备数据的新增/编辑/删除/导入记录在「变更记录」页。

### 恢复

```bash
cd ~/projects/dc-inventory
docker compose down
cp ~/backup/备份文件.db data/dc_inventory.db
docker compose up -d
```

### 迁移到新服务器

1. 新机装 Docker + Docker Compose
2. 拷贝整个 `dc-inventory/` 目录（`data/` 带上即带走全部数据）
3. 防火墙放行 5173
4. `docker compose up -d`

## 6. 账号与安全

| 事项 | 操作 |
|---|---|
| 默认账号 | `admin / admin123`，**首次登录必须改密**（右上角 → 修改密码） |
| 建用户 | admin 登录 → 用户管理 → 新增（admin=全部权限 / editor=改数据 / viewer=只读） |
| JWT 密钥 | `backend/app/auth.py` 默认占位 `SECRET_KEY`，**正式使用前通过环境变量设置随机长字符串**：`DCAM_SECRET_KEY=...`（在 docker-compose.yml 的 backend.environment 里填，或 `export` 后重启容器），改完所有人需重新登录 |
| Token 有效期 | 环境变量 `TOKEN_EXPIRE_HOURS`，默认 12 小时 |

### 忘记 admin 密码

```bash
cd ~/projects/dc-inventory
docker compose exec backend python -c "
from app.auth import hash_password
import sqlite3
con = sqlite3.connect('/app/data/dc_inventory.db')
con.execute('update users set password_hash=? where username=?', (hash_password('新密码'), 'admin'))
con.commit()
print('done')
"
```

## 7. 故障排查

| 现象 | 排查步骤 |
|---|---|
| 打不开页面（5173） | ① `docker compose ps` 两容器是否 Up；② `sudo ufw status` 规则是否还在；③ `docker compose logs frontend` |
| 页面能开但提示"网络错误" | ① `curl http://127.0.0.1:5173/api/health`；② `docker compose logs backend` 看报错 |
| backend 状态一直 unhealthy | `docker compose logs backend`；常见为数据库文件权限问题（`ls -la data/`） |
| 提示"登录已失效" | JWT 过期（12 小时），重新登录即可 |
| 导入 Excel 报错 | 看导入结果弹窗的行级错误；对照模板检查类型/状态/日期格式 |
| 容器重启循环 | `docker compose logs --tail 50` 看崩溃原因；确认磁盘没满（`df -h`） |

接口自测：

```bash
curl http://127.0.0.1:5173/api/health
# 期望输出 {"status":"ok"}
```

## 8. 快速巡检清单

```bash
cd ~/projects/dc-inventory
docker compose ps                                   # 两容器 Up，backend healthy
curl -s http://127.0.0.1:5173/api/health            # 链路通
ls -lh data/dc_inventory.db                         # 数据库文件在、大小正常
ls ~/backup/ | tail -3                              # 最近备份在
df -h / | tail -1                                   # 磁盘没满
```

## 附录：裸机方式运行（备用，不用 Docker 时）

```bash
# 启动 / 停止
cd ~/projects/dc-inventory && ./start.sh    # 日志在 /tmp/dc-inventory-*.log
./stop.sh

# 数据库位置为 backend/dc_inventory.db（与 Docker 方式的 data/ 不同，注意别混用）
# 手动启动（调试用，日志直接打屏幕）：
cd backend && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```
