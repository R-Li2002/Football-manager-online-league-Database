# Fly.io 免费额度优化方案

## 📊 Fly.io 免费额度政策详解

### 1. 免费额度津贴（每月）

| 资源类型 | 免费额度 | 说明 |
|---------|---------|------|
| **共享 CPU VM** | 3 台 shared-cpu-1x 256MB | 价值约 $6/月 |
| **存储容量** | 3GB | 超出部分 $0.15/GB/月 |
| **出站流量** | 160GB | 超出部分 $0.10/GB/月 |
| **SSL 证书** | 无限 | 完全免费 |
| **IPv6 地址** | 免费 | 无需额外费用 |
| **IPv4 地址** | ❌ $2/月/个 | 从免费额度中扣除 |

### 2. VM 定价（按秒计费）

**共享 CPU 类型（推荐）**：

| 配置 | CPU | RAM | 价格/月 |
|------|-----|-----|---------|
| shared-cpu-1x | 1 共享 | 256MB | **$2.02** ✅ |
| shared-cpu-1x | 1 共享 | 512MB | $3.32 |
| shared-cpu-1x | 1 共享 | 1GB | $5.92 |
| shared-cpu-2x | 2 共享 | 512MB | $4.04 |

**性能 CPU 类型（不推荐，价格高 10-15 倍）**：
- performance-1x 2GB：**$32.19/月**

---

## 🎯 Heigo 项目资源评估

基于项目特点（FastAPI + SQLite + 轻量级 Web）：

| 资源项 | 预估用量 | 免费额度 | 状态 |
|--------|---------|---------|------|
| VM | 1 台 | 3 台 | ✅ 充足 |
| 存储 | <1GB | 3GB | ✅ 充足 |
| 流量 | 5-10GB | 160GB | ✅ 充足 |
| IPv4 | 1 个 | 需付费 | ⚠️ $2/月 |

**预计月成本：$0（仅 IPv6）或 $2（含 IPv4）**

---

## ⚙️ 已实施优化措施

### 1. fly.toml 配置优化

已更新 `fly.toml` 文件，包含以下优化：

```toml
[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true      # ⭐ 闲置自动停止
  auto_start_machines = true     # ⭐ 需要时自动启动
  min_machines_running = 0       # ⭐ 最小运行 0 台
  
  [http_service.concurrency]
    type = "connections"
    hard_limit = 25              # 限制最大并发
    soft_limit = 20
  
  [[http_service.checks]]
    grace_period = "10s"
    interval = "30s"
    method = "GET"
    timeout = "5s"
    path = "/"                   # 健康检查路径

[http_service.http_options]
  compress = true                # ⭐ 启用 Gzip 压缩

[[vm]]
  cpu_kind = "shared"            # ⭐ 使用共享 CPU
  cpus = 1
  memory_mb = 256                # ⭐ 最小内存配置
```

**优化效果**：
- ✅ 闲置时自动停止，节省资源
- ✅ 启用压缩，减少流量
- ✅ 限制并发，防止资源耗尽
- ✅ 健康检查，确保服务可用

### 2. 健康检查端点

已在 `main1.py` 中添加健康检查端点：

```python
@app.get("/health")
async def health_check():
    """健康检查端点，用于 Fly.io 监控"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

**用途**：
- Fly.io 定期检查服务状态
- 自动重启故障实例
- 监控服务可用性

### 3. 监控脚本

创建了 `fly_monitor.py` 监控脚本：

```bash
# 使用方法
python fly_monitor.py
```

**功能**：
- ✅ 实时查询资源使用量
- ✅ 成本估算
- ✅ 阈值告警
- ✅ 使用日志记录

**配置方法**：
1. 获取 Fly.io API Token：
   ```bash
   fly auth token
   ```

2. 编辑 `fly_monitor.py`：
   ```python
   FLY_API_TOKEN = "your_fly_api_token"
   ORG_SLUG = "your_org_slug"
   ALERT_EMAIL = "your_email@example.com"
   ```

3. 设置定时任务（每天执行）：
   ```bash
   # Linux/Mac
   crontab -e
   0 9 * * * cd /path/to/project && python fly_monitor.py
   
   # Windows (任务计划程序)
   ```

---

## 🚀 部署步骤

### 1. 应用优化配置

```bash
# 部署更新后的配置
fly deploy
```

### 2. 调整 VM 配置

```bash
# 确保使用最小配置
fly scale vm shared-cpu-1x --memory 256MB

# 确保只有 1 台 VM
fly scale count 1
```

### 3. 查看状态

```bash
# 查看应用状态
fly status

# 查看日志
fly logs

# 查看监控面板
fly dashboard
```

---

## 📈 监控与告警

### 1. 日常监控命令

```bash
# 查看应用状态
fly status

# 查看 VM 配置
fly scale show

# 查看 Volume 使用
fly volumes list

# 查看实时日志
fly logs --tail

# 查看监控指标
fly dashboard
```

### 2. 告警阈值设置

| 指标 | 安全阈值 | 告警阈值 | 危险阈值 |
|------|---------|---------|---------|
| VM 费用 | <$4/月 | $4-6/月 | >$6/月 |
| 存储使用 | <2GB | 2-3GB | >3GB |
| 流量使用 | <100GB | 100-160GB | >160GB |
| 总成本 | <$6/月 | $6-10/月 | >$10/月 |

### 3. 定期检查清单

**每日检查**：
- [ ] 查看 `fly status` 确认应用运行正常
- [ ] 检查日志是否有异常

**每周检查**：
- [ ] 运行 `fly_monitor.py` 查看使用量
- [ ] 检查 Volume 使用量

**每月检查**：
- [ ] 审查 Fly.io 账单
- [ ] 根据实际使用情况调整配置

---

## ⚠️ 超出免费额度应对方案

### 场景 1：VM 费用超限

**症状**：VM 费用超过$6/月

**应对措施**：
```bash
# 1. 立即检查运行的 VM 数量
fly status
fly scale count 1

# 2. 降级 VM 配置
fly scale vm shared-cpu-1x --memory 256MB

# 3. 确认自动缩容已启用
fly scale show
```

### 场景 2：存储超限

**症状**：Volume 使用超过 3GB

**应对措施**：
```bash
# 1. SSH 连接到实例
fly ssh console

# 2. 清理日志文件
rm -rf /app/data/*.log

# 3. 压缩数据库
sqlite3 /app/data/heigo.db "VACUUM;"

# 4. 退出并检查
exit
fly volumes list
```

### 场景 3：流量超限

**症状**：出站流量超过 160GB/月

**应对措施**：
1. 检查是否有异常流量
2. 优化前端资源加载
3. 启用浏览器缓存
4. 考虑升级付费计划

### 场景 4：意外高额费用

**症状**：账单远超预期

**紧急措施**：
```bash
# 立即停止应用
fly apps stop heigo-league-db

# 查看详细账单
fly orgs show {org_slug}

# 联系 Fly.io 支持
# 邮箱：support@fly.io
```

---

## 💡 性能优化建议

### 1. 数据库优化

```python
# 使用索引（已在 models.py 中实现）
class Player(Base):
    uid = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    team_name = Column(String, index=True)

# 定期清理数据库
VACUUM;
```

### 2. API 缓存（可选）

```python
# 使用 fastapi-cache
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")

@app.get("/api/players")
@cache(expire=60)  # 缓存 60 秒
async def get_players():
    ...
```

### 3. 前端优化

- ✅ 已实现懒加载详情数据
- ✅ 已移除后台预加载
- ✅ 使用浏览器缓存
- ✅ 压缩 CSS/JS 文件

---

## 📋 成本对比

### 方案 A：极致免费（$0/月）

```toml
[http_service]
  auto_stop_machines = true
  min_machines_running = 0
# 不使用 IPv4，仅 IPv6
```

**优点**：
- ✅ 完全免费
- ✅ 不浪费资源

**缺点**：
- ⚠️ 首次访问需要冷启动（5-10 秒）
- ⚠️ 仅 IPv6，部分地区兼容性差

### 方案 B：稳定运行（$2/月，推荐）

```toml
[http_service]
  auto_stop_machines = false
  min_machines_running = 1
# 使用 IPv4
```

**优点**：
- ✅ 24/7 在线，无冷启动
- ✅ IPv4 兼容性好
- ✅ 成本极低

**缺点**：
- ⚠️ 需要支付$2/月 IPv4 费用

### 方案 C：性能优化（$5-8/月）

```toml
[[vm]]
  memory_mb = 512  # 升级到 512MB

[http_service]
  auto_stop_machines = true
```

**优点**：
- ✅ 更多内存，性能更好
- ✅ 自动缩容，按需计费

**缺点**：
- ⚠️ 成本稍高（$3.32 + $2 = $5.32/月）

---

## 🎯 推荐实施方案

### 阶段 1：立即实施（已完成）

- [x] 优化 fly.toml 配置
- [x] 添加健康检查端点
- [x] 创建监控脚本

### 阶段 2：优化实施（1-2 周内）

- [ ] 部署更新后的配置
- [ ] 设置定时监控任务
- [ ] 配置告警通知

### 阶段 3：长期监控（持续）

- [ ] 每月审查账单
- [ ] 根据使用情况调整配置
- [ ] 用户量增长时考虑升级

---

## 📞 支持资源

### Fly.io 官方文档
- [配置参考](https://fly.io/docs/reference/configuration/)
- [监控与告警](https://fly.io/docs/dashboard/)
- [定价说明](https://fly.io/docs/about/pricing/)

### 获取帮助
- Fly.io 社区：https://community.fly.io
- 技术支持：support@fly.io
- 状态页面：https://status.fly.io

---

## 📝 总结

### 关键要点
- ✅ Fly.io 采用**按使用量计费**模式，有**免费额度津贴**
- ✅ Heigo 项目可完全在免费额度内运行
- ✅ 启用**自动缩容**是节省成本的关键
- ✅ 使用**最小 VM 配置**（shared-cpu-1x 256MB）
- ✅ 定期**监控使用量**，设置告警阈值

### 预计成本
- **$0/月**：仅 IPv6，自动缩容
- **$2/月**：含 IPv4，24/7 在线
- **$5-8/月**：性能优化方案

### 下一步行动
1. 部署更新后的配置：`fly deploy`
2. 配置监控脚本并设置定时任务
3. 定期检查使用量和账单

按照此方案，Heigo 联赛数据库系统可在 Fly.io 免费额度内**长期稳定运行**！
