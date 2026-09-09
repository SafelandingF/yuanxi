# 缘析本地技术方案

Vue 页面访问本地 FastAPI，后端从 SQLite 读取虚构人物、保存会话，通过兼容 Chat Completions 的 API 调用外部模型。API Key 仅由后端读取根目录 `config.yaml`；无需部署、本地大模型或复杂 Agent 框架。

## 产品与模块

产品流程为“完善个人资料 → 匹配助手多轮对话与卡片选人 → 约会规划”，详细状态见 [产品设计](agent-product-design.md)。

| 模块 | 职责 |
| --- | --- |
| `backend/main.py`、`bootstrap.py` | 应用生命周期与依赖装配。 |
| `backend/api/` | HTTP 接口、异常响应与 SSE 编码。 |
| `backend/services/` | 会话、并发、幂等和结果持久化。 |
| `backend/agents/` | 独立画像、匹配与约会 Agent，工具定义和执行。 |
| `backend/domain/` | 输入与结果结构、评分、筛选、预算等纯规则。 |
| `backend/infrastructure/` | 模型协议、SQLite 和虚构样本。 |
| `AgentWorkspace.vue` | 单栏对话、每轮折叠工具记录、固定输入框、按需展开筛选、停止和幂等重试。 |
| `AgentCard.vue` | 画像、筛选条件、候选、对比、确认和空结果六种卡片及动作。 |

前端使用 Vue 3、Vite、shadcn-vue/Reka UI 和 AI Elements Vue 的 MessageResponse，底层 vue-stream-markdown 处理流式 Markdown。采用暖白与陶土橙主题。

分层职责见 [后端说明](../backend/README.md)，Agent 调用与扩展方法见 [Agent 实现说明](../backend/agents/README.md)。

## 模型协议

- Base URL 和模型名：按服务商填写 `llm.base_url`、`llm.model`，模板使用 `provider: openai-compatible`。
- 保留旧的仅 Key 配置兼容：默认使用原方舟地址和豆包 Pro。
- `POST /chat/completions`，`Authorization: Bearer <apikey>`。
- 匹配对话：`stream: true`、`tools`、`tool_choice: auto`；拼接 `delta.tool_calls[index]` 的名称和参数，收到正常 `tool_calls` 结束才执行。结果以 `role: tool` 和原始 `tool_call_id` 回传模型。
- 只向前端转发公开回复 `delta.content`。内部 `reasoning_content` 不消费、不存储；仅方舟模式发送 `thinking` 扩展参数（默认 disabled），通用模式不发送。
- 画像和约会分析：`response_format: {type: json_object}`，经 Pydantic 和业务约束校验。结构错误最多重试一次。
- 429/502/503/504 在消费响应前最多重试三次，等待 5、15、30 秒；中途断流不重播，正常结束标记缺失或截断均视为失败。

官方资料：[Chat Completions](https://www.volcengine.com/docs/82379/1494384)、[模型文档](https://www.volcengine.com/docs/82379/1795150)。已用真实方舟 API 验证 Pro 的原生流式工具调用、多轮筛选、对比及约会生成。

## 工具与数据约束

`analyze_profile` 提炼资料；`update_preferences` 以补丁更新筛选（未传字段保留，null/空兴趣清除限制）；`search_candidates` 在本地库按硬条件过滤和规则排序，返回至多三人；`compare_candidates` 只接受已经展示过的候选编号。

选择工具 `select_candidate` 由用户的卡片动作确定性触发，模型没有该工具的自主确认权限。后端检查候选属于最新推荐且卡片 revision 一致；约会接口另外检查 selected_id，不能绕过选择步骤。

用户可要求换一批，检索排除当前条件下已见过的候选。零结果保持原条件，返回空结果卡，等待用户决定放宽。画像、模型文字不修改数值评分；共同点和差异卡片基于真实字段生成。

匹配分：基础 35 + 共同兴趣最多 24 + 相同节奏 15 + 同城 10 + 相同关系目标 10 + 年龄接近 0–6，上限 98。全部人物虚构，分数不代表现实恋爱概率。

约会只使用本地活动目录，按双方预算较低值限制费用，验证活动 ID 和时间。每周 2–3 次与每月 1–2 次的频率差异触发一次 10 分修正，并把约会分析交给匹配助手解释；重复生成不累计扣分。

## 接口与卡片协议

| 接口 | 用途 |
| --- | --- |
| `GET /api/health` | 公开状态、模型名、候选数，不含配置密钥。 |
| `POST /api/agent/sessions` | 校验完整 Profile 后立即建立会话，无需等待模型。 |
| `GET /api/agent/sessions/{id}` | 恢复公开会话（不返回发送模型的内部消息序列）。 |
| `POST /api/agent/sessions/{id}/chat` | request_id、text、可选 selection（candidate_id、revision），返回 SSE。 |
| `POST /api/date/plan` | 会话、确认对象、预算、时间和口味，返回行程及流式解释。 |
| `POST /api/analyze` | 保留旧版固定流程接口供回归验证，当前前端不再调用。 |

每帧为 `data: {JSON}\n\n`：

- `delta`：新增公开 Markdown 文本。
- `tool_start` / `tool_end`：同一 id 对应实际执行、输入、状态与结果；匹配工具记录耗时。
- `card`：`{component, props, revision}`；服务端控制组件白名单和 props 来源。为轻量 A2UI 风格协议，不是完整 A2UI 标准实现。
- `state`：对话成功提交后的完整公开状态。
- `stage` / `result`：约会执行阶段及校验后的行程。
- `done` / `error`：明确的成功或失败结束。

## 一致性与恢复

每轮复制已存会话，在副本上执行工具。只有模型完整结束后才提交会话和工具消息，失败/取消不保存半轮修改。前端失败卡片禁用，旧版本卡片不可选择。一个会话同一时刻只有一轮修改，其他请求返回 409。

request_id 防止网络重试重复提交；相同编号但不同请求返回 409。最多 6 次模型工具循环，每次最多 5 个工具请求；每会话最多 30 轮，完整工具请求/响应顺序保存，避免孤立 tool_call。

SQLite 保存会话与完成的约会；最近一次约会也附在当前会话上，仅在候选与推荐版本未变时写入，刷新可恢复。修改筛选、重新检索或选择其他对象时清除该约会入口。浏览器保存会话编号和资料草稿，禁止保存模型密钥。

当前只面向本机单用户 Demo，无账号、真实人物匹配、商家搜索、地图、订位或部署。
