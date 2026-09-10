# 缘析 · Yuanxi

一个在本机运行的婚恋匹配与约会规划课设 Demo：填写个人资料，与匹配助手聊天、调整条件和选择候选，再生成约会安排。人物和活动来自本地虚构数据，模型接入兼容 OpenAI Chat Completions 协议的外部 API。

**Windows 用户优先按下面 4 步操作，命令在 PowerShell 中执行。** macOS / Linux 命令见后面的独立章节。 前端、后端和 SQLite 都在本机，无需部署或本地安装大模型；调用外部模型需要联网。

## 1. 准备环境

需要安装：

- Python **3.11 或以上**，安装时勾选 **Add python.exe to PATH**。
- Node.js **20.19+ 或 22.12+**，包含 npm。
- Git（用于拉取代码；也可以下载仓库 ZIP 后解压）。
- 一个兼容 Chat Completions 协议的模型服务，以及对应的 API Key、Base URL 和模型名。

安装完成后重新打开 PowerShell，检查版本：

```powershell
python --version
node --version
npm.cmd --version
```

如果 `python` 打开 Microsoft Store 或找不到命令，可先尝试 `py --version`；确认版本符合要求后，后面创建虚拟环境的命令也可以用 `py` 替代 `python`。若两者均不可用，请检查 Python 安装和 PATH。

在准备存放项目的文件夹打开 PowerShell，获取代码：

```powershell
git clone https://github.com/SafelandingF/yuanxi.git
cd yuanxi
```

仓库为私有仓库，需要有访问权限并完成 GitHub 身份验证。也可在 GitHub 下载 ZIP，解压后进入项目文件夹。后续命令都在同时包含 `run.py`、`frontend/` 和 `backend/` 的仓库根目录执行。

## 2. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

这里直接运行虚拟环境里的 Python，**不用执行 `Activate.ps1`**。使用 `npm.cmd` 可避免 PowerShell 对 `npm.ps1` 的执行策略限制，无需修改系统执行策略。

无需手动激活虚拟环境，也不需要单独安装或初始化数据库。首次启动会自动创建 `data/yuanxi.db`，从随仓库分发的 `datasets/candidates.json` 填入 1,200 位虚构候选。旧版本重启会自动补齐新增人物，保留聊天记录。换机器只需拉取包含数据文件的仓库并按本文运行，不需要复制原机器的数据库。详见 [数据与迁移说明](datasets/README.md)。

## 3. 配置模型

不需要在启动前手动编辑配置文件。首次打开页面时，如果尚未配置 API Key，应用会弹出模型设置窗口；填写服务商提供的 API Key、API 地址和模型名称，点击“保存并进入”即可。以后可以通过页面右上角的“模型设置”修改配置。

不限定 API Key 所属公司，弹窗中的三项对应以下配置：

```yaml
apikey: "YOUR_API_KEY"
llm:
  provider: "openai-compatible"
  base_url: "https://your-provider.example/v1"
  model: "YOUR_MODEL_ID"
```

这是通用占位模板，不能直接使用其中的地址或模型名。`base_url` 填写服务商的 API 根地址（包含其版本路径），不要附加 `/chat/completions`；后端会自动追加。密钥通过 `Authorization: Bearer` 发送。

服务和模型需要同时支持 **Chat Completions、原生工具调用（tool calling）、JSON 输出（response_format: json_object）和 SSE 流式响应**。仅有 API Key 并不意味着所有模型都兼容；仅支持其他协议的服务需要额外适配。若服务不接受 `temperature` 或 `max_tokens` 等标准参数，也需要适配后使用。

完整选项见 [配置模板](config.template.yaml)。通用模式不会发送方舟专属的 `thinking` 参数。现有只填写 `apikey` 的旧配置继续使用原来的方舟默认地址和模型；新接入其他服务请完整填写上述三项，并使用 `provider: openai-compatible`。也兼容 `llm.api_key`，顶层 `apikey` 优先。

配置成功后，后端会在本机生成或更新 `config.yaml`。该文件已被 Git 忽略；状态接口不会返回密钥，前端也不会把密钥保存到浏览器。可以提交模板，不能提交真实配置或把密钥放到前端环境变量中。

## 4. 启动并体验

```powershell
.\.venv\Scripts\python.exe .\run.py
```

以后每次运行，只需在仓库根目录执行这条命令，不用重复安装依赖或复制配置。没有模型配置时服务也可以启动，并由页面弹窗引导完成配置。

出现前后端启动成功的信息后，打开 [本地页面](http://127.0.0.1:5173/)。保持终端运行；按 **Ctrl+C** 同时停止两个服务。配置或后端代码变化后，停止并重新执行启动命令。

第一次演示可以这样走：

1. 点击“填入示例”，检查资料后保存，进入匹配助手。
2. 等待真实画像与检索结果。展开每轮操作记录，可以看工具输入和返回值。
3. 输入“只看杭州同城，24 到 29 岁”，观察筛选结果变化。
4. 点击“比较前两位”，再在人物行或对比结果中点击选择。
5. 点击“安排约会”，填写预算、开始时间和口味，生成行程。
6. 试着停止、重试或刷新页面，查看对话恢复。旧推荐默认折叠，过期结果不能再选。

[健康检查](http://127.0.0.1:8000/api/health) 在配置完成后返回 `status: ok`；尚未配置时返回 `status: setup_required`。[接口文档](http://127.0.0.1:8000/docs) 可查看请求字段。健康检查正常代表本地服务已启动，真实模型权限以发送一轮对话为准。

## Windows：分别启动（可选）

通常使用上面的一条启动命令即可。需要分开查看日志时，在仓库根目录打开两个 PowerShell 窗口。

窗口一启动后端：

```powershell
.\.venv\Scripts\python.exe -m backend
```

窗口二启动前端：

```powershell
npm.cmd --prefix frontend run dev
```

默认端口为前端 5173、后端 8000。如果把 `config.yaml` 的 `app.port` 改为 8001，单独启动前端时需设置同样的代理端口：

```powershell
$env:YUANXI_BACKEND_PORT = "8001"
npm.cmd --prefix frontend run dev
```

使用 `run.py` 时会自动同步这个端口，不需要手动设置。分别启动时，需要在两个窗口分别按 Ctrl+C 停止。

## macOS / Linux 运行

进入仓库根目录后安装依赖：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

按第 3 步填写配置；首次复制可用以下命令保留已有配置，再用文本编辑器打开 `config.yaml`：

```sh
if [ ! -f config.yaml ]; then cp config.template.yaml config.yaml; fi
.venv/bin/python run.py
```

若系统 `python3` 版本不足 3.11，请改用已安装的新版 Python 创建虚拟环境。单独启动时使用 `.venv/bin/python -m backend` 与 `npm --prefix frontend run dev`；自定义后端端口时用 `YUANXI_BACKEND_PORT=8001 npm --prefix frontend run dev`。

## 运行不起来时

| 现象                                      | 需要检查                                                                      |
| ----------------------------------------- | ----------------------------------------------------------------------------- |
| `python` 无法识别或打开 Microsoft Store | 安装 Python 并加入 PATH，重新打开 PowerShell；也可尝试`py`。                |
| `npm.ps1` 被禁止运行                    | 使用本文的`npm.cmd` 命令，无需改执行策略。                                  |
| 找不到模块或虚拟环境                      | 是否使用 Python 3.11+ 创建`.venv`，是否完成两端依赖安装。                   |
| 配置读取失败                              | 根目录是否存在`config.yaml`，YAML 缩进是否正确，`apikey` 是否仍是占位符。 |
| 密钥无效、无模型权限、模型不存在          | 检查服务商的 API Key、模型开通情况及`llm.model`。                           |
| 请求受限或较长时间等待                    | 服务商可能触发每分钟配额。后端有有限重试；失败后可从对话中重试。              |
| 端口被占用                                | 停止此前启动的那组服务，再运行一次。                                          |
| 页面无法连接后端                          | 查看后端终端；分别启动时确认代理端口与`app.port` 一致。                     |
| 对话达到轮次限制                          | 每段最多 30 轮，重新保存个人资料开启新对话。                                  |

数据库和配置保留在本机，重启不会删除。页面“重新开始”开启新的资料流程，历史记录仍在本地数据库中。

## 验证代码

后端测试使用测试模型和临时数据库，**不需要真实 Key，也不会消耗模型额度**：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
npm.cmd --prefix frontend run build
```

macOS / Linux 将 Python 路径替换为 `.venv/bin/python`，将 `npm.cmd` 替换为 `npm`。真实模型联调会产生正常 API 用量。现有检查及验证范围见 [验证记录](docs/verification.md)。

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
  infrastructure/            兼容 Chat Completions 的模型适配、SQLite、虚构样本
  core/                      配置读取
  tests/                     回归、协议、分层及生命周期检查
data/                        本地 SQLite，Git 忽略
```

- 想理解后端结构：读 [后端分层说明](backend/README.md)。
- 想解释课设的 Agent 能力：读 [Agent 实现说明](backend/agents/README.md)。
- 想理解页面和交互：读 [产品设计](docs/agent-product-design.md)。
- 组件来源和许可：[第三方许可说明](THIRD_PARTY_NOTICES.md)。

人物全部虚构，适配分只辅助比较，不代表恋爱概率。约会费用为本地活动估价，不含交通费；当前没有真实商家、地图、订位或联系他人的能力。

## 桃花小签（民俗娱乐）

侧栏的“桃花小签”由真实 AI 读取咸池规则，结合出生日期时间、出生地、感情状态、流年和补充问题进行推算与流式解读。规则位于 `backend/agents/rules/romance.md`，程序只校验输入，不计算桃花映射。支持时间不详和一键填入虚构演示资料。使用当前模型配置并消耗 API 额度；输入会发送给配置的模型服务，本应用不保存查询，也不影响匹配评分。民俗娱乐，AI 推算可能有误，不是完整历法排盘或恋爱概率预测。详见 [模块说明](docs/romance-research.md)。
