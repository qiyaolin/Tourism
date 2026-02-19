# Project Atlas Progress Tracker

## Header

- project: `Project Atlas`
- last_session_summary: `用户已确认第 1、2 步运行态验收成功，并指示将 Phase 1.9 暂时标记为完成。`
- current_focus: `Web 端优先：已完成 1.7-002 与 2.1 运行态验收，推进后续阶段任务`
- global_blockers: `无`
- next_session_bootstrap:
  - `读取本文件并输出：当前阶段/当前任务/阻塞项/下一步动作`
  - `执行 Phase 2.1 运行态验收：公开页借鉴->登录回跳->编辑器打开副本`
  - `执行 Phase 2.2 运行态验收：副本 diff 接口返回字段级差异`
  - `补做并收口 Phase 1.9 Web 安全基础测试（SQL 注入/XSS/CSRF）`

## Task Table

| task_id | phase | title | status | owner | updated_at | files_changed | verification | blocker | next_action |
|---|---|---|---|---|---|---|---|---|---|
| P1-1.1-001 | Phase 1.1 | 基础设施搭建（前端/后端/DB/联调） | done | codex | 2026-02-18T00:00:00+08:00 | `frontend/*`, `backend/*`, `infra/*`, `README.md` | `health/live=ok`, `health/ready=ready`, Python compileall 通过 | 无 | 转入 Phase 1.2 |
| P1-1.2-001 | Phase 1.2 | 用户系统初始化（数据模型+认证骨架） | done | codex | 2026-02-18T00:00:00+08:00 | `backend/app/api/v1/auth.py`, `backend/app/services/auth_service.py`, `backend/app/security/*`, `backend/app/models/*`, `backend/alembic/*`, `frontend/src/App.vue`, `frontend/src/services/auth.ts`, `frontend/src/composables/useAuth.ts`, `frontend/src/utils/validators.ts`, `backend/pyproject.toml`, `backend/Dockerfile`, `infra/docker-compose.yml` | `docker compose ps` 三服务 up（postgres healthy）；`GET /health/live`=200；`GET /health/ready`=200+db ok；`POST /auth/send-code`=200；`POST /auth/login`=200；`GET /auth/me`=200；错误验证码=401；无效 token=401；发码限流=429；前端 build 用户手工通过 | 无 | 转入 Phase 1.3 |
| P1-1.3-001 | Phase 1.3 | POI/行程/节点数据模型与 CRUD API（P0） | done | codex | 2026-02-18T00:00:00+08:00 | `backend/app/models/poi.py`, `backend/app/models/itinerary.py`, `backend/app/models/itinerary_item.py`, `backend/app/schemas/poi.py`, `backend/app/schemas/itinerary.py`, `backend/app/services/poi_service.py`, `backend/app/services/itinerary_service.py`, `backend/app/api/v1/pois.py`, `backend/app/api/v1/itineraries.py`, `backend/alembic/versions/20260218_0002_create_poi_itinerary_tables.py`, `backend/app/api/v1/router.py`, `backend/app/db/types.py` | Alembic 升级 `20260218_0001 -> 20260218_0002` 通过；POI CRUD 实测通过；行程 CRUD 实测通过；节点创建/更新/删除通过；day_index 越界返回 400；认证 token 访问受保护接口通过；`health/ready`=200 | 无 | 转入 Phase 1.4 P0 |
| P1-1.4-001 | Phase 1.4 | 地图引擎接入与基础交互（P0） | done | codex | 2026-02-17T22:07:01.1067806-05:00 | `backend/app/schemas/itinerary.py`, `backend/app/services/itinerary_service.py`, `backend/app/api/v1/itineraries.py`, `backend/tests/test_itinerary_items_with_poi.py`, `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/.env.example`, `frontend/src/env.d.ts`, `frontend/src/api.ts`, `frontend/src/composables/useAmap.ts`, `frontend/src/components/PoiInfoCard.vue`, `frontend/src/App.vue`, `frontend/src/styles.css`, `infra/docker-compose.yml`, `frontend/.env(本地未纳入版本控制)`, `AGENTS.md`, `PROGRESS.md` | `uv run --python 3.14 pytest -q`=2 passed；`uv run --python 3.14 ruff check app/services/itinerary_service.py app/api/v1/itineraries.py app/schemas/itinerary.py tests/test_itinerary_items_with_poi.py`=passed；`pnpm build`=passed；运行态联调通过（地图加载、marker 渲染、点击卡片显示）；中文字段修复完成（行程标题、地址、tips）；用户最终确认“现在都正常了” | 无 | 转入 Phase 1.5 P0（仅推进 P0 + 稳定门禁） |
| P1-1.5-001 | Phase 1.5 | 时间轴编辑器（P0） | done | codex | 2026-02-18T12:50:00+08:00 | `frontend/src/App.vue`, `frontend/src/api.ts`, `frontend/src/components/TimelineEditor.vue`, `frontend/src/components/AddTimelineBlockDialog.vue`, `frontend/src/types/timeline.ts`, `AGENTS.md`, `PROGRESS.md`, `DB:pois(测试种子)` | `pnpm lint`=passed；`pnpm build`=passed；景点总数=10；`qmark_count=0`；浏览器运行态联调验收合格（新增/删除/拖拽/保存/地图联动） | 无 | 转入 Phase 1.6 P0（AI 内容引擎） |
| P1-1.6-001 | Phase 1.6 | AI 内容引擎（P0） | done | codex | 2026-02-18T14:21:15-05:00 | `backend/app/core/config.py`, `backend/app/schemas/ai_engine.py`, `backend/app/services/ai_engine_service.py`, `backend/app/api/v1/ai_engine.py`, `backend/app/api/v1/router.py`, `backend/tests/test_ai_engine_service.py`, `backend/.env.example`, `backend/pyproject.toml`, `backend/Dockerfile`, `frontend/src/api.ts`, `frontend/src/components/AiPlanGenerator.vue`, `frontend/src/App.vue`, `frontend/src/styles.css`, `infra/docker-compose.yml`, `backend/uv.lock`, `.gitignore`, `backend/.env(本地未纳入版本控制)`, `PROGRESS.md` | `uv run ruff check app/services/ai_engine_service.py tests/test_ai_engine_service.py`=passed；`uv run pytest -q tests/test_ai_engine_service.py`=8 passed；`pnpm lint`=passed；`pnpm build`=passed；`POST /api/v1/ai/preview`=200（Gemini链路可达）；运行态复验 `POST /api/v1/ai/preview`（模糊文本）=422，`detail.error_code=AI_UNGROUNDED_ITEMS`；前端 422 解析兼容修复后 `pnpm lint`=passed、`pnpm build`=passed；用户浏览器验收通过（422错误卡片+继续手动编辑+正向导入链路） | 无 | 进入 Phase 1.7 需求梳理与任务拆分 |
| P1-1.6-002 | Phase 1.6 | Gemini 提供商切换与真实连通性验证 | done | codex | 2026-02-18T14:03:44-05:00 | `infra/docker-compose.yml`, `backend/app/core/config.py`, `backend/.env(本地未纳入版本控制)`, `PROGRESS.md` | 容器环境读取为 `AI_PROVIDER=gemini` 与 `GEMINI_MODEL=gemini-3-flash-preview`；`POST /api/v1/ai/preview` 返回 200 | 无 | 转入输出质量收敛（提示词与语义校验） |
| P1-1.7-001 | Phase 1.7 | 基础 Dashboard（探索广场）P0 | done | codex | 2026-02-18T14:48:30-05:00 | `backend/app/models/itinerary.py`, `backend/app/schemas/itinerary.py`, `backend/app/services/itinerary_service.py`, `backend/app/services/ai_engine_service.py`, `backend/app/api/v1/explore.py`, `backend/app/api/v1/router.py`, `backend/alembic/versions/20260218_0003_itinerary_status_and_cover.py`, `backend/tests/test_explore_service.py`, `backend/tests/test_itinerary_items_with_poi.py`, `backend/tests/test_ai_engine_service.py`, `frontend/src/App.vue`, `frontend/src/router.ts`, `frontend/src/main.ts`, `frontend/src/api.ts`, `frontend/src/styles.css`, `frontend/src/pages/EditorWorkbenchPage.vue`, `frontend/src/pages/LoginPage.vue`, `frontend/src/pages/ExplorePage.vue`, `frontend/src/pages/PublicItineraryPage.vue`, `frontend/src/pages/MyItinerariesPage.vue`, `frontend/package.json`, `frontend/pnpm-lock.yaml`, `PROGRESS.md` | `uv run ruff check app/api/v1/explore.py app/services/itinerary_service.py app/models/itinerary.py app/schemas/itinerary.py app/services/ai_engine_service.py tests/test_explore_service.py tests/test_itinerary_items_with_poi.py tests/test_ai_engine_service.py`=passed；`uv run pytest -q`=15 passed；`pnpm lint`=passed；`pnpm build`=passed；用户运行态验收通过（`/explore`、`/itineraries/:id`、`/mine`、`/editor`） | 无 | 按用户决策进入 Web-only 路线：执行 Phase 1.9（剔除移动端项） |
| P1-1.9-001 | Phase 1.9 | Web 端验收：端到端流程（注册→AI生成→编辑→发布→浏览） | done | codex | 2026-02-18T22:14:28-05:00 | `PROGRESS.md` | 用户手动验收通过（Web 端主链路可用）；移动端项按 Web-only 规则暂缓；按用户指令暂时将 1.9 标记为完成 | 无 | 后续如恢复安全专项，可追加独立安全验收任务 |
| P2-2.1-001 | Phase 2.1 | 一键借鉴（Fork）系统 P0（发布快照复制） | done | codex | 2026-02-18T22:14:28-05:00 | `backend/app/models/itinerary_fork.py`, `backend/app/models/itinerary_snapshot.py`, `backend/app/models/__init__.py`, `backend/app/services/itinerary_service.py`, `backend/app/api/v1/explore.py`, `backend/app/api/v1/itineraries.py`, `backend/app/schemas/itinerary.py`, `backend/alembic/versions/20260218_0004_fork_and_snapshot.py`, `backend/tests/test_fork_and_diff_service.py`, `frontend/src/api.ts`, `frontend/src/pages/PublicItineraryPage.vue`, `frontend/src/pages/LoginPage.vue`, `frontend/src/router.ts`, `frontend/src/pages/MyItinerariesPage.vue`, `frontend/src/pages/EditorWorkbenchPage.vue`, `PROGRESS.md` | `uv run ruff check app/services/itinerary_service.py app/api/v1/explore.py app/api/v1/itineraries.py tests/test_fork_and_diff_service.py alembic/versions/20260218_0004_fork_and_snapshot.py`=passed；`uv run pytest -q`=17 passed；`pnpm lint`=passed；`pnpm build`=passed；用户已确认借鉴链路运行态通过（公开页借鉴->登录回跳->编辑器副本） | 无 | 维持能力稳定，按需推进 2.2/后续功能 |
| P2-2.2-001 | Phase 2.2 | 版本快照与最小 Diff API 预埋（字段级差异） | done | codex | 2026-02-19T00:56:35-05:00 | `backend/app/services/itinerary_service.py`, `backend/app/schemas/itinerary.py`, `backend/app/api/v1/itineraries.py`, `backend/alembic/versions/20260218_0004_fork_and_snapshot.py`, `backend/tests/test_fork_and_diff_service.py`, `frontend/src/api.ts`, `PROGRESS.md` | 运行态联调完成：正向 `summary.added=1/modified=1`，`metadata_fields` 命中 `title/status/visibility`，`added_keys` 命中 `d2-s1`，`modified_keys` 命中 `d1-s1`；负向非 fork 行程请求 diff 返回 404；`uv run pytest -q tests/test_fork_and_diff_service.py`=2 passed | 无 | 进入 Diff View UI 收尾与用户复测 |
| P2-2.2-002 | Phase 2.2 | 编辑器内 Diff View UI（字段级高亮） | test_passed | codex | 2026-02-19T01:32:01-05:00 | `frontend/src/components/ItineraryDiffPanel.vue`, `frontend/src/pages/EditorWorkbenchPage.vue`, `frontend/src/styles.css`, `PROGRESS.md` | `pnpm lint`=passed；`pnpm build`=passed；完成“行程元信息”可读性修复：字段中文映射（标题/目的地/天数/状态/可见范围/封面）、状态与可见性值中文化、空值统一“未设置”、未知字段兜底“其他信息（字段名）” | 待用户关闭旧标签页后重开并手工复测 UI 交互 | 用户复测“行程元信息”前后值是否可读、枚举与空值文案是否符合预期 |
| P1-1.7-002 | Phase 1.7 | 我的行程/编辑器补充作废与取消按钮 | done | codex | 2026-02-18T22:14:28-05:00 | `frontend/src/api.ts`, `frontend/src/components/ConfirmDialog.vue`, `frontend/src/pages/MyItinerariesPage.vue`, `frontend/src/pages/EditorWorkbenchPage.vue`, `PROGRESS.md` | `pnpm lint`=passed；`pnpm build`=passed；确认动作改为站内 UI 对话框（不再使用 `window.confirm`）；在线核验：`http://localhost:5173/src/pages/MyItinerariesPage.vue` 与 `http://localhost:5173/src/pages/EditorWorkbenchPage.vue` 均命中 `ConfirmDialog` 特征；用户确认第 1 步运行态验收成功 | 无 | 进入后续阶段开发 |
| GOV-WEB-ONLY-001 | Governance | 开发范围锁定为 Web 端（移动端暂缓） | done | codex | 2026-02-18T14:46:58-05:00 | `PROGRESS.md`, `Project_Atlas_开发手册_Checklist.md`, `Project_Atlas_开发规划书_V2.0.md` | 用户明确确认“现阶段只专注 Web 端开发，暂不考虑移动端”；三份文档已同步更新范围口径 | 无 | 后续需求评审与任务拆分默认仅包含 Web 端 |
| DOC-TRACK-001 | Governance | 跨 session 进度追踪机制落地 | done | codex | 2026-02-18T00:00:00+08:00 | `AGENTS.md`, `PROGRESS.md`, `README.md` | 文档结构与规则字段已落地 | 无 | 后续按规则持续更新 |
| BASELINE-LOCK-001 | Governance | 锁文件纳入进度基线管理 | done | codex | 2026-02-18T00:00:00+08:00 | `AGENTS.md`, `PROGRESS.md`, `backend/uv.lock`, `frontend/pnpm-lock.yaml` | 确认锁文件存在并纳入规则追踪 | 无 | 后续依赖变更时同步记录锁文件变化 |
| GOV-PHASE-SYNC-001 | Governance | Phase 收尾“更新到最新版”规则落地 | done | codex | 2026-02-18T21:10:44-05:00 | `AGENTS.md`, `PROGRESS.md` | 版本一致性复核通过：`docker exec atlas-frontend /app/src/pages/PublicItineraryPage.vue` 含 Fork 特征；`http://localhost:5173/src/pages/PublicItineraryPage.vue` 含 `forkPublicItinerary` 与 `以此为模板`；`http://localhost:5173/src/pages/LoginPage.vue` 含 `fork_source/auto_fork` 回跳逻辑 | 无 | 后续每个 Phase 进入 done 前强制执行最新版同步核验 |

## Changelog (Newest First)

- 2026-02-19T01:32:01-05:00
  - 变更：修复 Diff 面板“行程元信息”可读性问题，重写 `ItineraryDiffPanel` 的元信息展示逻辑，新增字段中文映射、状态/可见性枚举中文化、空值统一文案与未知字段兜底显示。
  - 结论：元信息展示不再直接暴露 `title/status/visibility/null` 等技术值；前端门禁 `pnpm lint`、`pnpm build` 均通过。
  - 风险：仍需用户侧关闭旧标签页后重新打开页面做最终 UI 复测确认。

- 2026-02-19T00:56:35-05:00
  - 变更：完成 Phase 2.2 全量落地，新增编辑器内 Diff View（`ItineraryDiffPanel`），在保存面板接入“查看修改对比/收起修改对比”与按需拉取 `GET /itineraries/{id}/diff`，支持 metadata/added/removed/modified 三类差异展示与三色高亮。
  - 结论：`P2-2.2-001` 运行态联调阻塞已解除并更新为 `done`；新增 `P2-2.2-002` 状态为 `test_passed`，静态门禁与版本一致性核验通过。
  - 风险：尚待用户侧手工复测 UI 交互；复测前需关闭旧标签页后重新打开页面，避免命中旧缓存。

- 2026-02-18T22:14:28-05:00
  - 变更：根据用户反馈“第 1、2 步已验证成功”，将 `P1-1.7-002` 与 `P2-2.1-001` 从 `test_passed` 更新为 `done`；并按用户指令将 `P1-1.9-001` 暂时标记为 `done`。
  - 结论：当前阻塞项清空，阶段状态按用户决策完成收口。
  - 风险：Phase 1.9 的安全专项（SQL 注入/XSS/CSRF）未单独执行；如后续恢复安全专项，需新增独立验收任务追踪。

- 2026-02-18T21:32:05-05:00
  - 变更：将作废确认从浏览器通知改为站内 UI 对话框，新增 `ConfirmDialog` 组件并接入 `我的行程` 与 `编辑器` 两处作废流程。
  - 结论：前端门禁通过（`pnpm lint`、`pnpm build`），在线源码核验命中 `ConfirmDialog`，不再依赖 `window.confirm`。
  - 风险：仍需用户侧运行态点击确认“取消/确认作废”交互文案与行为符合预期。

- 2026-02-18T21:26:55-05:00
  - 变更：补充行程作废与取消入口：`我的行程` 各状态卡片新增“作废行程”；`编辑器` 保存面板新增“取消更改”与“作废当前行程”按钮，并接入行程删除 API。
  - 结论：前端静态与构建门禁通过（`pnpm lint`、`pnpm build`），交互能力已落地。
  - 风险：尚未完成用户侧运行态验收，需在浏览器实际验证作废与取消路径。

- 2026-02-18T21:10:44-05:00
  - 变更：重启 `atlas-frontend` 以同步运行态版本，并在 `AGENTS.md` 新增“## 13. Phase 完成后的版本同步（强制）”。
  - 结论：`http://localhost:5173/` 已命中最新版代码特征（Fork 按钮与登录回跳逻辑在线可见）。
  - 风险：若浏览器仍打开旧标签页，用户侧可能继续命中旧缓存；复测需关闭旧标签页后重新打开页面。

- 2026-02-18T16:55:00-05:00
  - 变更：完成 Phase 2.1/2.2 代码落地：新增 `itinerary_snapshots` 与 `itinerary_forks` 模型及迁移，新增公开页 Fork API 与副本 Diff API，扩展行程溯源字段；前端新增“以此为模板”、登录回跳继续借鉴、我的行程/编辑器溯源展示。
  - 结论：自动化门禁通过（后端 ruff + pytest，前端 lint + build），`P2-2.1-001` 与 `P2-2.2-001` 状态更新为 `test_passed`。
  - 风险：运行态验收尚未执行；`P1-1.9-001` 安全基础测试仍未收口，项目总体仍非 `done`。

- 2026-02-18T14:54:20-05:00
  - 变更：记录用户反馈“Web 端验收子任务已手动验证成功”，新增 `P1-1.9-001` 并标记为 `test_passed`。
  - 结论：Phase 1.9 的 Web 端 E2E 主链路验收已通过。
  - 风险：安全基础测试与性能基线尚未执行，Phase 1.9 仍未收口为 `done`。

- 2026-02-18T14:46:58-05:00
  - 变更：根据用户最新决策将项目范围锁定为 Web 端，更新 `PROGRESS.md` 当前焦点、下一步动作与治理任务 `GOV-WEB-ONLY-001`，明确移动端阶段暂缓。
  - 结论：后续开发与验收默认按 Web-only 口径执行。
  - 风险：`Phase 1.9` 中“移动端浏览体验测试”需显式排除，避免误触发跨范围工作。

- 2026-02-18T14:48:30-05:00
  - 变更：根据用户“已经验证通过”反馈，补记 Phase 1.7 P0 运行态验收结果，并将 `P1-1.7-001` 状态由 `test_passed` 更新为 `done`。
  - 结论：Phase 1.7 P0 完整闭环（自动化门禁 + 运行态验收均通过）。
  - 风险：无新增阻塞项。

- 2026-02-18T14:39:17-05:00
  - 变更：完成 Phase 1.7 P0 前端实现，新增 `Vue Router` 路由层（`/explore`、`/itineraries/:id`、`/mine`、`/editor`、`/login`），落地探索广场、公开详情页、我的行程管理页，并接入发布/撤回与封面 URL 编辑；新增依赖 `vue-router` 并更新 `frontend/pnpm-lock.yaml`。
  - 结论：Phase 1.7 P0 代码与自动化门禁通过（后端 ruff+pytest，前端 lint+build），任务状态提升至 `test_passed`。
  - 风险：尚未完成浏览器端运行态验收，暂不升级为 `done`。

- 2026-02-18T14:35:06-05:00
  - 变更：完成 Phase 1.7 P0 后端改造，新增探索广场公开接口（列表/详情/公开节点）、行程状态扩展（`in_progress`）、封面字段（`cover_image_url`）与对应迁移；补充公开接口与状态流转单测。
  - 结论：后端契约已满足 Dashboard P0，门禁通过（目标文件 ruff + 全量 pytest）。
  - 风险：前端路由与页面尚未完成，任务仍为 `in_progress`。

- 2026-02-18T14:21:15-05:00
  - 变更：记录用户运行态最终验收结果，并将 `P1-1.6-001` 状态由 `test_passed` 更新为 `done`。
  - 结论：Phase 1.6 P0 闭环完成（异常链路与正向导入链路均通过）。
  - 风险：无新增阻塞项。
- 2026-02-18T14:17:40-05:00
  - 变更：修复前端未命中 422 专用 UI 的问题；`previewAiPlan` 改为对 422 响应进行宽松 JSON 解析（不依赖特定 content-type），并新增 `isAiPreviewValidationError` 类型守卫；`AiPlanGenerator` 改为守卫分支显示结构化错误。
  - 结论：避免回落到通用错误文案 `Preview AI plan request failed with 422...`，422 业务错误可进入专用交互卡片。
  - 风险：仍需浏览器端最终验收确认用户环境已加载最新前端产物（关闭旧标签页后重开）。
- 2026-02-18T14:14:44-05:00
  - 变更：补齐运行态复验，按最新接口契约（`raw_text + itinerary_id`）完成登录、创建行程、调用 AI 预览链路验证。
  - 结论：模糊文本输入（“这次就想随便逛逛，不想太累，慢慢走。”）触发 422，且 `error_code=AI_UNGROUNDED_ITEMS`，增强约束生效。
  - 风险：终端输出仍可能受本地代码页影响出现中文显示异常，需以前端页面与 API 原始 JSON 为准继续验收。
- 2026-02-18T14:11:58-05:00
  - 变更：新增“原文证据约束”语义校验：当 AI 生成地点与原文无匹配依据时返回 `AI_UNGROUNDED_ITEMS`（422）；补充对应单测与地点匹配函数测试。
  - 结论：对于“随便逛逛”类模糊输入，系统不再接受凭空地点结果，改为可解释失败并引导重试/手动编辑。
  - 风险：证据匹配当前使用轻量字符串规则，后续可能需要更强的中文同义归一化策略。

- 2026-02-18T14:03:44-05:00
  - 变更：按“时间块字段规范化”重构 Gemini 提示词；后端新增 AI 语义校验（空 items/非法 day_index/空 name）并返回结构化 422；前端新增 422 专用交互（展示 reason/摘要/建议动作，支持“继续手动编辑”）；修复配置读取大小写问题并确认 Gemini 链路可达。
  - 结论：空结果不再静默通过，失败可解释可重试；Gemini 调用链路恢复为可用（200）。
  - 风险：Gemini 输出仍可能出现“语义弱但结构合法”，需在运行态继续观察并迭代提示词。

- 2026-02-18T13:45:47-05:00
  - 变更：执行 Gemini 真实连通性测试并修复环境注入链路（compose backend 改为读取 `backend/.env`，Settings 启用 `case_sensitive=False`）。
  - 结论：请求已到达 Gemini 上游；当前 `gemini-3.0-flash` 返回 404，不可用于现有 `v1beta generateContent`；`gemini-2.0-flash` 返回 429（配额超限）。
  - 风险：Gemini 目前不可用于生产调用，需先解决模型可用性与配额。

- 2026-02-18T13:45:47-05:00
  - 变更：新增 AI 提供商可切换能力（`AI_PROVIDER=deepseek|gemini`），后端新增 Gemini `generateContent` 调用链路并保持原接口不变；补充配置样例与 provider 分支单测。
  - 结论：在不改前端接口的前提下可临时切换到 Gemini；后端静态检查与单测通过。
  - 风险：切换 Gemini 前必须配置有效 `GEMINI_API_KEY`，否则会返回 503。

- 2026-02-18T13:38:32-05:00
  - 变更：修复 AI 预览 404 的版本不一致问题（重建 backend 容器使 `httpx` 依赖与新路由生效），并将容器启动参数改为非 `--reload`，消除 `.pytest_cache` 权限导致的 watchfiles 崩溃风险。
  - 结论：`/api/v1/ai/preview` 路由在线，接口从 404 恢复为预期鉴权响应（401）。
  - 风险：容器内已禁用热重载，后续后端改动需手动重启容器生效。

- 2026-02-18T13:32:07-05:00
  - 变更：按用户提供密钥完成本地 `backend/.env` 的 `DEEPSEEK_API_KEY` 与 `AMAP_WEB_SERVICE_KEY` 配置，并补充 `.gitignore` 忽略 `backend/.env` 与 `frontend/.env`，降低误提交风险。
  - 结论：后端配置读取验证通过（环境变量存在且可被 `get_settings()` 读取）。
  - 风险：密钥已在对话中明文出现，建议尽快在供应商控制台轮换后再继续联调。

- 2026-02-18T13:24:57-05:00
  - 变更：完成 Phase 1.6 P0 代码落地（DeepSeek 预览与导入 API、POI 先库内后高德匹配、前端 AI 预览与确认导入组件接入）。
  - 结论：静态与自动化门禁通过（后端 ruff+pytest，前端 lint+build），`P1-1.6-001` 更新为 `test_passed`。
  - 风险：尚未完成浏览器运行态验收（真实 DeepSeek/高德联调与导入链路），暂不升级为 `done`。

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
