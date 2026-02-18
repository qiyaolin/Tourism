# Project Atlas Progress Tracker

## Header

- project: `Project Atlas`
- last_session_summary: `Phase 1.5 P0 浏览器运行态联调验收合格，任务已收口为 done。`
- current_focus: `Phase 1.6 AI 内容引擎（P0）准备阶段`
- global_blockers: `无`
- next_session_bootstrap:
  - `读取本文件并输出：当前阶段/当前任务/阻塞项/下一步动作`
  - `确认本地后端与前端可启动，健康检查可通过`
  - `读取本文件并确认 P1-1.5-001 的 dev_done 证据（lint/build）`
  - `执行 Phase 1.5 运行态联调（新增/删除/拖拽/保存/地图双向联动）`

## Task Table

| task_id | phase | title | status | owner | updated_at | files_changed | verification | blocker | next_action |
|---|---|---|---|---|---|---|---|---|---|
| P1-1.1-001 | Phase 1.1 | 基础设施搭建（前端/后端/DB/联调） | done | codex | 2026-02-18T00:00:00+08:00 | `frontend/*`, `backend/*`, `infra/*`, `README.md` | `health/live=ok`, `health/ready=ready`, Python compileall 通过 | 无 | 转入 Phase 1.2 |
| P1-1.2-001 | Phase 1.2 | 用户系统初始化（数据模型+认证骨架） | done | codex | 2026-02-18T00:00:00+08:00 | `backend/app/api/v1/auth.py`, `backend/app/services/auth_service.py`, `backend/app/security/*`, `backend/app/models/*`, `backend/alembic/*`, `frontend/src/App.vue`, `frontend/src/services/auth.ts`, `frontend/src/composables/useAuth.ts`, `frontend/src/utils/validators.ts`, `backend/pyproject.toml`, `backend/Dockerfile`, `infra/docker-compose.yml` | `docker compose ps` 三服务 up（postgres healthy）；`GET /health/live`=200；`GET /health/ready`=200+db ok；`POST /auth/send-code`=200；`POST /auth/login`=200；`GET /auth/me`=200；错误验证码=401；无效 token=401；发码限流=429；前端 build 用户手工通过 | 无 | 转入 Phase 1.3 |
| P1-1.3-001 | Phase 1.3 | POI/行程/节点数据模型与 CRUD API（P0） | done | codex | 2026-02-18T00:00:00+08:00 | `backend/app/models/poi.py`, `backend/app/models/itinerary.py`, `backend/app/models/itinerary_item.py`, `backend/app/schemas/poi.py`, `backend/app/schemas/itinerary.py`, `backend/app/services/poi_service.py`, `backend/app/services/itinerary_service.py`, `backend/app/api/v1/pois.py`, `backend/app/api/v1/itineraries.py`, `backend/alembic/versions/20260218_0002_create_poi_itinerary_tables.py`, `backend/app/api/v1/router.py`, `backend/app/db/types.py` | Alembic 升级 `20260218_0001 -> 20260218_0002` 通过；POI CRUD 实测通过；行程 CRUD 实测通过；节点创建/更新/删除通过；day_index 越界返回 400；认证 token 访问受保护接口通过；`health/ready`=200 | 无 | 转入 Phase 1.4 P0 |
| P1-1.4-001 | Phase 1.4 | 地图引擎接入与基础交互（P0） | done | codex | 2026-02-17T22:07:01.1067806-05:00 | `backend/app/schemas/itinerary.py`, `backend/app/services/itinerary_service.py`, `backend/app/api/v1/itineraries.py`, `backend/tests/test_itinerary_items_with_poi.py`, `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/.env.example`, `frontend/src/env.d.ts`, `frontend/src/api.ts`, `frontend/src/composables/useAmap.ts`, `frontend/src/components/PoiInfoCard.vue`, `frontend/src/App.vue`, `frontend/src/styles.css`, `infra/docker-compose.yml`, `frontend/.env(本地未纳入版本控制)`, `AGENTS.md`, `PROGRESS.md` | `uv run --python 3.14 pytest -q`=2 passed；`uv run --python 3.14 ruff check app/services/itinerary_service.py app/api/v1/itineraries.py app/schemas/itinerary.py tests/test_itinerary_items_with_poi.py`=passed；`pnpm build`=passed；运行态联调通过（地图加载、marker 渲染、点击卡片显示）；中文字段修复完成（行程标题、地址、tips）；用户最终确认“现在都正常了” | 无 | 转入 Phase 1.5 P0（仅推进 P0 + 稳定门禁） |
| P1-1.5-001 | Phase 1.5 | 时间轴编辑器（P0） | done | codex | 2026-02-18T12:50:00+08:00 | `frontend/src/App.vue`, `frontend/src/api.ts`, `frontend/src/components/TimelineEditor.vue`, `frontend/src/components/AddTimelineBlockDialog.vue`, `frontend/src/types/timeline.ts`, `AGENTS.md`, `PROGRESS.md`, `DB:pois(测试种子)` | `pnpm lint`=passed；`pnpm build`=passed；景点总数=10；`qmark_count=0`；浏览器运行态联调验收合格（新增/删除/拖拽/保存/地图联动） | 无 | 转入 Phase 1.6 P0（AI 内容引擎） |
| DOC-TRACK-001 | Governance | 跨 session 进度追踪机制落地 | done | codex | 2026-02-18T00:00:00+08:00 | `AGENTS.md`, `PROGRESS.md`, `README.md` | 文档结构与规则字段已落地 | 无 | 后续按规则持续更新 |
| BASELINE-LOCK-001 | Governance | 锁文件纳入进度基线管理 | done | codex | 2026-02-18T00:00:00+08:00 | `AGENTS.md`, `PROGRESS.md`, `backend/uv.lock`, `frontend/pnpm-lock.yaml` | 确认锁文件存在并纳入规则追踪 | 无 | 后续依赖变更时同步记录锁文件变化 |

## Changelog (Newest First)

- 2026-02-18T12:50:00+08:00
  - 变更：根据用户确认“浏览器运行态联调验收合格”，完成 Phase 1.5 P0 收口并将 `P1-1.5-001` 更新为 `done`。
  - 结论：Phase 1.5 P0 质量门禁闭环（静态检查、构建、运行态验收）。
  - 风险：无新增阻塞，建议按规划转入 Phase 1.6 P0。

- 2026-02-18T12:42:00+08:00
  - 变更：修复 `AddTimelineBlockDialog` 数值解析函数对非字符串输入不兼容导致的运行态崩溃（`value.trim is not a function`）。
  - 结论：填写信息后点击“确认添加景点”不再因 `trim` 调用崩溃中断。
  - 风险：仍需浏览器端完成完整交互回归确认（新增/删除/拖拽/保存/地图联动）。

- 2026-02-18T12:35:00+08:00
  - 变更：修复“新增时间块窗口填写后无反应”的可观测性问题；提交前增加景点与天数显式校验，并在窗口内显示错误信息；提交按钮文案调整为“确认添加景点”。
  - 结论：避免静默失败，用户可直接看到失败原因并重试。
  - 风险：仍需你在浏览器端完成交互回归，确认“填写信息 -> 确认添加景点”稳定生效。

- 2026-02-18T12:28:00+08:00
  - 变更：按“稳定 UTF-8 写入方案”补充初始景点测试数据（颐和园、北海公园、南锣鼓巷、景山公园、国家博物馆、天安门广场、798艺术区、奥林匹克公园）。
  - 结论：景点总数提升至 10 条，数据库无 `?` 污染，已满足时间轴“添加时间块”联调数据量需求。
  - 风险：仍需你在浏览器完成运行态主链路验收后，任务才能升级为 `test_passed`。

- 2026-02-18T12:20:00+08:00
  - 变更：完成中文写入问题系统性分析并回退“新建地点”扩 scope；统一用户文案为“景点”；在 `AGENTS.md` 固化“中文写入稳定方案（UTF-8 文件优先、命令行内联用 `\\uXXXX`、写后三段校验）”。
  - 结论：确认乱码主要源自命令行编码链路，不是 DB/API 能力缺陷；已形成可复用的稳定修复路径。
  - 风险：尚未完成“补充初始景点供测试”的最终落地（当前仅确认数据库无 `?` 污染），需按新稳定链路补数并做运行态复验。

- 2026-02-18T12:05:00+08:00
  - 变更：修复时间轴“添加时间块”链路（对话框提交携带完整 POI 快照，移除二次查找失配风险，新增失败提示与新增成功未保存提示）；新增 `AGENTS.md` 中文字符异常处理流程；清理数据库历史乱码测试数据（删除标题/目的地/POI 名称含 `?` 的记录）。
  - 结论：新增时间块交互与中文数据源质量问题均完成代码与数据层修复，静态门禁通过。
  - 风险：仍需浏览器运行态完整回归（新增/删除/拖拽/保存/地图联动）后才能将任务升级为 `test_passed`。

- 2026-02-18T11:30:00+08:00
  - 变更：完成 Phase 1.5 P0 代码落地，新增 `TimelineEditor/TimelineBlock/AddTimelineBlockDialog` 组件，接入拖拽排序、按天编辑、地图双向联动、时间块增删与显式保存；扩展前端 API 客户端（POI 列表、行程节点增删改）；新增 `vuedraggable` 依赖并更新 `frontend/pnpm-lock.yaml`。
  - 结论：`P1-1.5-001` 状态更新为 `dev_done`，静态与构建门禁通过（`pnpm lint`、`pnpm build`）。
  - 风险：尚未执行浏览器运行态验收，需验证新增/删除/拖拽/保存/地图双向联动全链路后方可升级到 `test_passed`/`done`。

- 2026-02-17T22:07:01.1067806-05:00
  - 变更：完成 1.4 收尾验收并将 `P1-1.4-001` 由 `test_passed` 更新为 `done`。
  - 结论：地图主链路与中文显示问题均闭环，Phase 1.4 P0 达成。
  - 风险：无新增阻塞，后续进入 Phase 1.5 需继续遵循 P0+稳定门禁策略。

- 2026-02-17T22:03:47.2819931-05:00
  - 变更：在 `AGENTS.md` 新增“文本与编码规范（强制）”；对联调 POI 通过 API 以 UTF-8 JSON 重写中文标题。
  - 结论：编码治理规则已落地，数据源已按 UTF-8 路径修复。
  - 风险：PowerShell 控制台显示可能受本地代码页影响，需以前端页面显示结果为准。

- 2026-02-17T22:00:32.0733285-05:00
  - 变更：按高德 JS API 使用规范修复 Marker 方法调用，确保方法调用时 `this` 绑定到 marker 实例并增加异常降级；新增 AGENTS.md“第三方 API 文档优先规范（强制）”。
  - 结论：`pnpm build` 通过，系统性降低 `_opts/_isTop` 类内部状态错误风险。
  - 风险：仍需浏览器实测确认当前账号所选行程存在节点并完成 marker 点击链路。

- 2026-02-17T21:55:44.5471857-05:00
  - 变更：移除 marker `setTop` 调用（该调用触发高德内部 `_isTop` 赋值异常），聚焦仅使用 `setzIndex` + 可选动画。
  - 结论：前端构建通过，`atlas-frontend` 已重启并正常运行。
  - 风险：若浏览器缓存旧脚本，仍可能看到旧异常，需硬刷新。

- 2026-02-17T21:54:46.0081621-05:00
  - 变更：将 marker 动画/层级方法改为 `typeof === 'function'` 后再调用，避免 `setAnimation is not a function` 运行时异常。
  - 结论：`pnpm build` 通过，`atlas-frontend` 已重启并正常启动。
  - 风险：若浏览器缓存旧 bundle，需硬刷新（`Ctrl+Shift+R`）。

- 2026-02-17T21:50:01.2825639-05:00
  - 变更：安装并验证 Playwright MCP 全局服务（`@playwright/mcp`）。
  - 结论：`playwright-mcp --version` 返回 `0.0.68`，可用于后续浏览器自动化联调。
  - 风险：首次执行自动化任务前仍需确保浏览器依赖可用与 MCP 客户端侧正确接入。

- 2026-02-17T21:46:20.1570171-05:00
  - 变更：修复前端 `marker.setAnimation is not a function`（高德 Marker 能力兼容处理，改为可选调用）。
  - 结论：前端构建通过，marker 聚焦流程不再因动画方法缺失崩溃。
  - 风险：当前账号若所选行程无节点，仍会显示“暂无地点”，需切换到有点位行程。

- 2026-02-17T21:42:39.3342215-05:00
  - 变更：执行 1.4 运行态 API 联调并创建最小验收数据（1 行程 + 2 POI + 2 节点）。
  - 结论：主链路、空态场景、鉴权异常均验证通过，后端接口行为满足预期。
  - 风险：仍需浏览器侧确认 marker 点击弹卡后才能将任务收口为 `done`。

- 2026-02-17T21:35:57.3735146-05:00
  - 变更：使用新申请的高德 JS API Key 更新本地 `frontend/.env`，重建 `frontend` 容器并复验环境注入。
  - 结论：容器内 `VITE_AMAP_KEY` 前缀与长度校验通过（前缀 `3d62992b`，长度 32），Vite 服务启动正常。
  - 风险：若控制台来源白名单未放行 `localhost:5173`，仍可能出现底图空白。

- 2026-02-17T21:31:11.2829486-05:00
  - 变更：修复 compose 环境注入路径，`frontend` 服务改为读取 `../frontend/.env`，并重建前端容器。
  - 结论：容器内 `VITE_AMAP_KEY` 已注入真实值，不再是占位值。
  - 风险：若高德控制台未放行 `localhost:5173` 来源，地图仍可能无法加载。

- 2026-02-17T21:18:02.1240571-05:00
  - 变更：已在本地 `frontend/.env` 配置高德 Key，并复验前端构建与 lint。
  - 结论：自动化检查维持通过，Key 配置阻塞解除。
  - 风险：仍需运行态手工联调确认真实地图加载与交互链路。

- 2026-02-18T00:00:00+08:00
  - 变更：完成 Phase 1.4 P0 代码落地（后端新增 `GET /itineraries/{id}/items` 聚合接口；前端新增高德地图加载、行程选择、POI 打点与点击信息卡片）。
  - 结论：`P1-1.4-001` 标记为 `test_passed`，自动化检查通过。
  - 风险：未配置有效高德 Key 时无法完成真实地图运行态验收，当前未收口为 `done`。

- 2026-02-18T00:00:00+08:00
  - 变更：补充 `GeometryPoint.cache_ok=True`，消除 SQLAlchemy 类型缓存告警。
  - 结论：运行日志噪音降低，不影响现有接口行为。
  - 风险：无新增阻塞。

- 2026-02-18T00:00:00+08:00
  - 变更：完成 Phase 1.3 P0（POI/行程/节点三表 + 迁移 + CRUD API + 运行态验收）。
  - 结论：`P1-1.3-001` 标记为 `done`，系统可进行数据层与业务层联动开发。
  - 风险：1.3 的 P1/P2（层级结构搜索/批量导入）尚未开始。

- 2026-02-18T00:00:00+08:00
  - 变更：执行收尾检查并将 `P1-1.2-001` 从 `test_passed` 更新为 `done`。
  - 结论：Phase 1.2 全部 P0 目标闭环完成。
  - 风险：无新增阻塞，后续进入 Phase 1.3/1.4 时需持续维护鉴权一致性。

- 2026-02-18T00:00:00+08:00
  - 变更：完成 Phase 1.2 运行态验收（Docker 容器、Health、Auth 主链路与负向场景）。
  - 结论：`P1-1.2-001` 由 `dev_done` 更新为 `test_passed`。
  - 风险：尚未执行发布前收尾动作，任务未标记为 `done`。

- 2026-02-18T00:00:00+08:00
  - 变更：修复 backend 镜像构建失败（`pip install -e .` 包发现冲突），新增 setuptools 包发现约束并改为 `pip install .`。
  - 结论：`app` 与 `alembic` 顶层包冲突路径已消除，等待 Docker 构建复验。
  - 风险：若镜像内依赖拉取仍受网络限制，构建仍可能失败。

- 2026-02-18T00:00:00+08:00
  - 变更：完成 Phase 1.2 P0 代码实现（用户表、验证码、JWT、认证 API、登录注册前端）。
  - 结论：开发状态进入 `dev_done`，前端生产构建已通过。
  - 风险：后端尚未完成运行态验收，状态未达 `test_passed/done`。

- 2026-02-18T00:00:00+08:00
  - 变更：将 `backend/uv.lock` 与 `frontend/pnpm-lock.yaml` 纳入进度基线治理规则。
  - 结论：后续 session 将强制追踪锁文件状态，避免依赖漂移不可见。
  - 风险：若依赖更新后未同步记录锁文件变更，仍会造成基线偏差。

- 2026-02-18T00:00:00+08:00
  - 变更：新增跨 session 进度追踪规则，建立 `PROGRESS.md` 单一进度源。
  - 结论：后续 session 可直接恢复上下文并持续追踪状态流转。
  - 风险：时间戳与任务状态若不及时更新，将导致恢复精度下降。
