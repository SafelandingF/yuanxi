# 缘析 · Yuanxi

一个在本机运行的婚恋匹配与约会规划课设 Demo：填写个人资料，与匹配助手聊天、调整条件和选择候选，再生成约会安排。人物和活动来自本地虚构数据，模型使用火山方舟豆包 Pro API。

**第一次运行按下面 4 步操作。** 前端、后端和 SQLite 都在本机，无需部署或本地安装大模型；调用豆包需要联网。

## 1. 准备环境

需要安装：

- Python **3.11 或以上**。
- Node.js **20.19+ 或 22.12+**，包含 npm。
- 一个可以调用豆包模型的火山方舟 API Key。默认模型为 `doubao-seed-2-0-pro-260215`。

先进入本仓库根目录，也就是同时包含本文件、`run.py`、`frontend/` 和 `backend/` 的目录。后续命令都在根目录运行，不在 `backend/` 内运行。

检查版本：

```sh
python3 --version
node --version
npm --version
```

Windows 使用 `python` 替代 `python3`。如果 macOS 的 `python3` 是系统自带旧版本，请改用已安装的 `python3.11` 或更新版本完成下一步。

## 2. 安装依赖

macOS / Linux：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

无需手动激活虚拟环境，也不需要单独安装或初始化数据库。首次启动会自动创建 `data/yuanxi.db`，从随仓库分发的 `datasets/candidates.json` 填入 1,200 位虚构候选。旧版本重启会自动补齐新增人物，保留聊天记录。换机器只需拉取包含数据文件的仓库并按本文运行，不需要复制原机器的数据库。详见 [数据与迁移说明](datasets/README.md)。

## 3. 填写模型配置

如果已有根目录 `config.yaml`，保留现有配置。否则将 `config.template.yaml` 复制为 `config.yaml`，填写自己的密钥。

最小配置只需要一项：

```yaml
apikey: "你的火山方舟 API Key"
```

默认连接 `https://ark.cn-beijing.volces.com/api/v3`，使用豆包 Pro。需要换模型时，在同一个文件中增加：

```yaml
llm:
  model: "你已开通的豆包模型 ID 或 ep-... 接入点 ID"
```

完整字段见 [配置模板](config.template.yaml)。模型需要支持 Chat Completions、原生工具调用、JSON 输出与流式响应。也兼容旧的 `llm.api_key`，顶层 `apikey` 优先。

`config.yaml` 已被 Git 忽略，密钥只由后端读取。可以提交模板，不能提交真实配置或把密钥放到前端环境变量中。

## 4. 启动并体验

macOS / Linux：

```sh
.venv/bin/python run.py
```

Windows PowerShell：

```powershell
.venv\Scripts\python.exe run.py
```

出现前后端启动成功的信息后，打开 [本地页面](http://127.0.0.1:5173/)。保持终端运行；按 **Ctrl+C** 同时停止两个服务。配置或后端代码变化后，停止并重新执行启动命令。

第一次演示可以这样走：

1. 点击“填入示例”，检查资料后保存，进入匹配助手。
2. 等待真实画像与检索结果。展开每轮操作记录，可以看工具输入和返回值。
3. 输入“只看杭州同城，24 到 29 岁”，观察筛选结果变化。
4. 点击“比较前两位”，再在人物行或对比结果中点击选择。
5. 点击“安排约会”，填写预算、开始时间和口味，生成行程。
6. 试着停止、重试或刷新页面，查看对话恢复。旧推荐默认折叠，过期结果不能再选。

[健康检查](http://127.0.0.1:8000/api/health) 应返回 `status: ok`；[接口文档](http://127.0.0.1:8000/docs) 可查看请求字段。健康检查正常代表本地服务已启动，真实模型权限以发送一轮对话为准。

## 开发时分别启动

如果需要看两个独立终端的日志，可以分别运行：

```sh
.venv/bin/python -m backend
```

```sh
npm --prefix frontend run dev
```

默认端口是前端 5173、后端 8000。修改 `config.yaml` 中的 `app.port` 后，`run.py` 会自动将端口传给前端代理。单独启动前端时需要设置 `YUANXI_BACKEND_PORT` 为相同值，例如 macOS / Linux：

```sh
YUANXI_BACKEND_PORT=8001 npm --prefix frontend run dev
```

## 运行不起来时

| 现象 | 需要检查 |
| --- | --- |
| 找不到模块或虚拟环境 | 是否使用 Python 3.11+ 创建 `.venv`，是否完成两端依赖安装。 |
| 配置读取失败 | 根目录是否存在 `config.yaml`，YAML 缩进是否正确，`apikey` 是否仍是占位符。 |
| 密钥无效、无模型权限、模型不存在 | 检查方舟 Key、模型开通情况及 `llm.model`。 |
| 请求受限或较长时间等待 | 方舟可能触发每分钟配额。后端有有限重试；失败后可从对话中重试。 |
| 端口被占用 | 停止此前启动的那组服务，再运行一次。 |
| 页面无法连接后端 | 查看后端终端；分别启动时确认代理端口与 `app.port` 一致。 |
| 对话达到轮次限制 | 每段最多 30 轮，重新保存个人资料开启新对话。 |

数据库和配置保留在本机，重启不会删除。页面“重新开始”开启新的资料流程，历史记录仍在本地数据库中。

## 验证代码

后端测试使用测试模型和临时数据库，**不需要真实 Key，也不会消耗模型额度**：

```sh
.venv/bin/python -m unittest discover -s backend/tests -v
npm --prefix frontend run build
```

Windows 替换 Python 路径即可。真实模型联调会产生正常 API 用量。现有检查及验证范围见 [验证记录](docs/verification.md)。

## 代码与文档入口

```text
README.md                    环境准备、配置、启动与演示（本文件）
config.template.yaml         可提交的配置模板
config.yaml                  本机真实配置，Git 忽略
run.py                       同时启动和停止前后端
frontend/                    Vue 页面与交互组件
backend/
  README.md                  分层设计、依赖方向、修改位置
  main.py                    应用工厂与生命周期
  bootstrap.py               装配模型、仓库、Agent 和服务
  api/                       HTTP 接口与 SSE 编码
  services/                  会话、并发、幂等、保存结果
  agents/                    独立 Agent 层，含实现说明 README.md
  domain/                    数据结构、业务规则和依赖契约
  infrastructure/            火山方舟适配、SQLite、虚构样本
  core/                      配置读取
  tests/                     回归、协议、分层及生命周期检查
data/                        本地 SQLite，Git 忽略
```

- 想理解后端结构：读 [后端分层说明](backend/README.md)。
- 想解释课设的 Agent 能力：读 [Agent 实现说明](backend/agents/README.md)。
- 想理解页面和交互：读 [产品设计](docs/agent-product-design.md)。
- 组件来源和许可：[第三方许可说明](THIRD_PARTY_NOTICES.md)。

人物全部虚构，适配分只辅助比较，不代表恋爱概率。约会费用为本地活动估价，不含交通费；当前没有真实商家、地图、订位或联系他人的能力。
