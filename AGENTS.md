# AGENTS.md — 项目宪法

本仓库是 A2 治理原型的实现。规格见 [docs/SPEC.md](docs/SPEC.md)，实施顺序见 [docs/PLAN.md](docs/PLAN.md)。
**任何改动都不得违反本文件的六条硬规则。**

## 1. 运行环境

- Python **3.11+**（本机实测 3.15.0）。
- **零第三方运行时依赖**：只用标准库。禁止 `pip install` 才能跑通的代码路径。
- 无 git 时用 `SHA256SUMS` 快照替代 commit 标识，`app_version.txt` 为版本来源（缺省回落到 `config/config.json`）。

## 2. 六条不可协商的规则

1. **一条命令跑测试**：`python -m unittest discover -s tests -q`。项目统一用 `unittest`（本机无 pytest）；pytest 能发现 unittest 用例，接入时不冲突。
2. **一条命令自检**：`python -m govern.run --selftest`，输出形如 `ok: 6 tasks, 6 cards`。
3. **一条命令复现**：`python -m govern.run --batch --schedule config/schedule.json`，默认 `replay` 模式，**不联网、不需要密钥**。
4. **零魔法数字**：所有阈值、模型名、温度、seed、样本量只允许出现在 `config/*.json`。代码里出现这类字面量即为缺陷。
5. **无密钥无端点**：`sk-`、`api_key`、`token=`、`https://` 不得入库。密钥只从环境变量读取（`A2_API_KEY`），永不写文件、不写日志、不进截图。
6. **所有实验运行必须写 JSONL**：一次会话一个 `<session_id>.jsonl`，一次一行，字段见 [docs/SPEC.md](docs/SPEC.md) 4.2–4.3。日志是唯一数据源，指标只能由日志重算得出。

## 3. 模块约定

- 包根为 `govern/`，扁平结构，入口 `python -m govern.run`。
- 每个模块提供 `--selftest`（通过 `python -m govern.<module> --selftest` 调用），输出 `ok: ...` 并返回 0。
- 模块间只通过公开函数/数据类交互，不访问对方私有属性。
- LLM 调用**只能**出现在 `govern/llm.py`；其它模块一律走 `Client`。

## 4. 日志与隐私

- 日志只存 **hash + 长度**，不存原文（Q7）。校验器必须拒绝 `text` / `content` / `body` / `prompt_raw` 一类字段。
- `runs/` 不入版本库；保留期 `retention_days`（90 天），`govern.log --purge` 是唯一删除入口。
- `recordings/` 是 replay 的受控例外，只允许自建语料与作者自测产生的录制；**真人会话录制不得进入该目录**。

## 5. 提交前检查

1. `python -m unittest discover -s tests -q` 全绿。
2. `python -m govern.run --selftest` 输出与预期一致。
3. `python tools/scan_secrets.py` 零命中。
4. `python -m govern.provenance --check` 通过（M10 之后）。
5. 新增/变更的行为有对应测试；修复缺陷时先写失败测试。

## 6. 禁止事项

- 禁止把 planned 或 simulated 的行为描述成 implemented（评分红线，见 SPEC 0.2）。
- 禁止在报告或 UI 中声称采集了人类数据——本期为作者自测 + 录制回放。
- 禁止为了"看起来完成"而放松验收阈值；做不到就如实降级并记录在 `docs/` 中。
