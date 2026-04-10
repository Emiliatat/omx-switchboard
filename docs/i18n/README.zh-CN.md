# omx-switchboard

> 面向 Codex 的自主工作模式路由层。让 AI 自己判断什么时候保持原生执行、什么时候先规划、什么时候升级到更强工作流。

## Languages

- [English](../../README.md)
- [简体中文](./README.zh-CN.md)
- [日本語](./README.ja.md)

## 这是什么

`omx-switchboard` 是一个面向 Codex 的技能与启动器项目，它的核心目标不是让用户每次手动指定 `native`、`deep-interview`、`ralplan`、`ralph` 或 `team`，而是让系统根据任务特征自动选择合适的工作模式。

它主要做这些事：

- 小而明确的任务留在原生 Codex
- 模糊、目标不清的任务转到 `deep-interview`
- 设计或方案驱动的任务转到 `ralplan`
- 已经执行就绪的串行任务转到 `ralph`
- 只有在确实适合并行时才转到 `team`
- 以发现问题为主的请求转到 `code-review` 或 `security-review`

它提供两层能力：

1. `$omx-switchboard` 技能
2. `omxr` 启动器，用于每次都先做自动路由再执行

## 为什么做这个

原生 Codex、`deep-interview`、`ralplan`、`ralph` 和 `team` 都有各自适合的任务形态。

这个项目要解决的重点不是“哪个模式更省 token”，而是“让 AI 在正确的时候进入正确的模式”。这样用户不需要持续扮演调度器，不需要每次都先判断要不要切模式。

实际效果是：

- 简单任务保持轻量
- 需求不清的任务先做澄清和探索
- 方案型任务先做规划
- 已经明确可执行的任务直接进入实现
- 只有真的能拆成并行工作流时才启用 `team`

换句话说，模式选择应该成为系统行为，而不是用户反复手工控制的步骤。

## 安装后会得到什么

这个仓库当前提供的是实用安装流程，不是 marketplace 式的一键插件安装。

安装后会有：

- `~/.codex/skills/omx-switchboard` 下的技能目录
- `~/.local/bin` 下的 `omxr` 与 `omx-switchboard` 启动器

它目前不会：

- 自动注册到 Codex marketplace
- 通过独立插件商店步骤自动出现

最简单的理解方式是：

- 这是一个可以通过 GitHub 安装的技能加启动器项目
- 同时也带有面向未来插件化分发的 manifest

## 自动路由是怎么工作的

“自动”在这里有两层含义：

### 1. 隐式技能调用

仓库内置的 `openai.yaml` 允许 Codex 在识别到相关任务时自动引入 `$omx-switchboard`。

### 2. 确定性的默认入口

如果你希望每次输入任务时都先经过路由判断，可以直接使用安装后的 `omxr` 或 `omx-switchboard` 启动器。

这些启动器会：

- 先判断任务形态
- 生成或执行对应命令
- 在 `team` 或 `ralph` 的运行前提不满足时自动降级

这是“始终启用自动路由”的可靠做法。

## 路由规则

路由器会评估三个维度：

1. `ambiguity_score`
2. `scope_score`
3. `parallelism_score`

### 模糊度 `ambiguity_score`

满足一项加 1 分：

- 最终目标不清楚
- 验收标准缺失
- 边界或非目标没有说明
- 请求里使用了 `improve`、`optimize` 这类宽泛动词，但没有明确范围
- 请求仍然更像产品方向，而不是实现任务

解释：

- `0-1`：低模糊
- `2-3`：中等模糊
- `4-5`：高模糊

### 范围 `scope_score`

满足一项加 1 分：

- 可能涉及多个模块或子系统
- 至少隐含三个有分量的实施步骤
- 验证或测试本身需要实际工作
- 存在迁移或兼容性风险
- 很可能不是一次短执行就能完成

解释：

- `0-1`：小
- `2-3`：中
- `4-5`：大

### 并行度 `parallelism_score`

满足一项加 1 分：

- 至少能明确命名两条独立工作线
- 实现和验证可以并行
- 文档、迁移或发布可以独立推进
- 持久化的 tmux 或 worktree 协调确实有价值

解释：

- `0-1`：不要用 `team`
- `2`：可考虑
- `3-4`：强烈适合 `team`

## 决策顺序

按这个顺序应用：

1. 显式覆盖，如 `route:team` 或 `route:native`
2. 以发现问题为主的请求 -> `review`
3. 以安全为中心的请求 -> `security`
4. `ambiguity_score >= 3` -> `deep`
5. `scope_score >= 3` 且还没达到执行就绪 -> `plan`
6. `scope_score >= 3`、`parallelism_score >= 3` 且具备 tmux 条件 -> `team`
7. `scope_score >= 2` 且已经执行就绪 -> `ralph`
8. 其他情况 -> `native`

这里的“执行就绪”指的是目标、预期结果、验证方式已经足够明确，可以直接实现，而不需要先做一轮探索。

## 降级策略

如果更强模式当前不可用：

- `team -> ralph -> plan -> native`
- `ralph -> plan -> native`
- `plan -> native`

启动器会在解释输出里说明降级原因。

## 安装

### 前置要求

安装前请确认：

- 已安装 `git`
- Unix-like 系统有 `python3`
- Windows 有 `python` 或 `py -3`
- Codex 已经安装并完成基础配置

推荐：

- 把 `~/.local/bin` 加到 `PATH`

如果没有加入 `PATH`，也可以直接用完整路径运行：

- Unix-like: `~/.local/bin/omxr`
- Windows: `$HOME\\.local\\bin\\omxr.cmd`

### Unix-like

```bash
git clone https://github.com/Emiliatat/omx-switchboard.git
cd omx-switchboard
bash ./scripts/install.sh
```

### Windows PowerShell

```powershell
git clone https://github.com/Emiliatat/omx-switchboard.git
cd omx-switchboard
.\scripts\install.ps1
```

默认安装会做两件事：

- 把技能复制到 `~/.codex/skills/omx-switchboard`
- 把启动器安装到 `~/.local/bin`

安装后的启动器：

- `omxr`
- `omx-switchboard`

## 用法

### 直接使用技能

```text
$omx-switchboard
Fix the login timeout and choose the safest workflow automatically.
```

```text
$omx-switchboard route:plan
Design the safest migration path first. Do not execute yet.
```

```text
$omx-switchboard route:team
Split implementation, verification, and docs into parallel lanes.
```

### 使用始终自动路由的启动器

解释系统选择了哪条路线：

```bash
omxr route "Design the safest auth migration"
```

打印将要执行的命令：

```bash
omxr print "Fix the login timeout with verification"
```

自动路由并执行：

```bash
omxr "Fix the login timeout with verification"
```

等价显式形式：

```bash
omxr exec "Fix the login timeout with verification"
```

## 独立调度脚本

你也可以直接使用底层调度脚本：

```bash
python3 skills/omx-switchboard/scripts/dispatch_omx.py \
  --route auto \
  --task "Split implementation, tests, and docs in parallel" \
  --format json
```

## 发布信息

当前公开仓库：

- `https://github.com/Emiliatat/omx-switchboard`

如果你 fork 这个项目，记得同步修改这些公开元数据：

- `.codex-plugin/plugin.json`
- `LICENSE`
- `README.md`

## 致谢与归属

这个项目受 `oh-my-codex` 影响并与之协同工作。

如果你的版本包含来自 `oh-my-codex` 或 `cli-in-wechat` 的复制或改写内容，请保留上游 MIT 许可声明和归属说明。详见 [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。
