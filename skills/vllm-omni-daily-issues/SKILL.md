---
name: vllm-omni-daily-issues
description: >-
  Triage the vLLM-Omni nightly HTML report and file/update GitHub issues for
  performance regressions (>10% for 3+ consecutive days) and Buildkite/local
  failed cases. Use when the user asks to 提日报 issue、performance regression
  提 issue、nightly 报告分析提单, or daily issue triage from the nightly report.
---

# vLLM-Omni Daily Issues

从 nightly 日报中筛选需要提 issue 的模型,查重后在 `vllm-project/vllm-omni` 创建或更新 issue。
分两部分:**Part 1 性能回退 issue**;**Part 2 Buildkite/local failed case issue**。

## Prerequisite — 更新 kanban 仓库获取最新日报

日报由 kanban 仓库每日生成,操作前必须先拉最新代码:

```bash
cd /Users/congwang/Documents/GitHub/vllm-omni-kanban
git switch main && git pull --ff-only origin main
```

最新日报按文件名日期取最新一份:

```bash
ls -t /Users/congwang/Documents/GitHub/vllm-omni-kanban/data/nightly_test_report/ | head -1
# nightly-report-buildkite-latest-YYYY-MM-DD.html
```

若 `git pull --ff-only` 失败或工作区有意外改动,停下来报告,不要 force 操作。

---

## Part 1 — Performance regression issues

### 工作流

```
- [ ] 1. 解析日报 "All major regressions" 表,按模型聚合
- [ ] 2. 筛选候选:连续失败 >= 3 天 且 回退幅度 > 10%
- [ ] 3. GitHub 查重(open + closed)
- [ ] 4. 与用户确认清单后执行;首个 issue 先提一个让用户看格式
- [ ] 5. 新提 issue / 给已有 open issue 补评论
```

### Step 1 — 解析日报

运行解析脚本(自动找最新日报,也可传具体路径):

```bash
python scripts/parse_regressions.py
python scripts/parse_regressions.py --report <html> --model <keyword>
```

输出按模型聚合的回退行(天数、test、metric、幅度、config)及日报的
vllm 版本和 vllm-omni build commit(短哈希)。

完整 commit 哈希用 GitHub API 解析(本地仓库可能没有该 commit):

```bash
gh api repos/vllm-project/vllm-omni/commits/{短哈希} --jq .sha
```

### Step 2 — 筛选候选

- 入选:同一模型任一指标 **连续失败 >= 3 天**(报告列 `3 days` / `3 days+`)且幅度 **> 10%**。
- 幅度不足 10% 的只观察,不提(标题模板声明 "more than 10%",不符会失真)。
- 同系列模型、回退模式相同(同配置同测试)可合并一个 issue,如
  Qwen-Image-Edit + Qwen-Image-Edit-2511(先例 #4964 "Qwen-image-*")。
- NPU(910)与 GPU(H100)分开判断;某些模型(如 MiniCPM-o 910)用户可能明确不提,遵循用户决定。

### Step 3 — GitHub 查重

open 和 closed 都要查,关键字至少覆盖三类:

```bash
gh search issues --repo vllm-project/vllm-omni "performance metrics regressed" --limit 50 \
  --json number,title,state,createdAt
gh search issues --repo vllm-project/vllm-omni "performance drop" --limit 50 \
  --json number,title,state,createdAt
gh search issues --repo vllm-project/vllm-omni "{模型名关键字}" --limit 30 \
  --json number,title,state,createdAt
```

判定规则:

| 查重结果 | 动作 |
|----------|------|
| 无相关 issue,或只有 closed | 新提 issue |
| 有 open issue 覆盖同样的 test/metric | 不重复提;数据**明显恶化或出现新配置**时补评论 |
| open issue 标题是旧格式(如 "Performance drop - X") | 可改标题为标准格式并补数据(须为用户自己提的或经确认) |
| 昨天刚更新过评论、今天数据无本质变化 | 不再刷评论,避免噪音 |

### Step 4 — 与用户确认

把「需新提 / 已覆盖 / 边界情况」三类列表给用户讨论,确认后执行。
首个 issue 先单独提交一个,等用户确认格式再批量处理其余。

### Step 5 — 提 issue / 补评论

**标题模板:**

```
[Bug]: Nightly CI, {模型名}, performance metrics regressed by more than 10% compared to the baseline in some scenarios
```

**labels:** `bug` + `ci-failure`(`high priority` 留给维护者分诊)。

**正文模板**(数据行从解析脚本输出复制,按幅度降序;可包含 1~2 天的次要行作为补充):

```markdown
### Your current environment

<details>
<summary>The output of <code>python collect_env.py</code></summary>

```text
CI env
```

</details>


### Your code version

<details>
<summary>The commit id or version of vllm</summary>

```text
{vllm 版本,如 0.26.0}
```
</details>
<details>
<summary>The commit id or version of vllm-omni</summary>

```text
{vllm-omni 完整 commit 哈希}
```
</details>


### 🐛 Describe the bug

Source | Model | Hardware | Type | Config | Test | Metric | latest | baseline | vs baseline | Status | Days failing
-- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | --
{数据行}

### Before submitting a new issue...

- [x] Make sure you already searched for relevant issues, and asked the chatbot living at the bottom right corner of the [documentation page](https://vllm-omni.readthedocs.io), which can answer lots of frequently asked questions.
```

创建命令用 heredoc 保证格式:

```bash
gh issue create --repo vllm-project/vllm-omni \
  --title "..." --label bug --label ci-failure \
  --body "$(cat <<'EOF'
{正文}
EOF
)"
```

**补评论模板**(给已有 open issue 更新数据):

```markdown
Update from the {YYYY-MM-DD} nightly report (vllm-omni commit [{短哈希}](https://github.com/vllm-project/vllm-omni/commit/{完整哈希})): {一句话说明变化,如持续/恶化/新增配置}.

{当日数据表格,列同正文模板}
```

**Baseline 偏高的特殊情况:** 若历史曲线显示当前性能其实可接受,是 baseline
定得太高,则 issue 正文只列代表性的一条数据,并在评论区补充说明建议调整
baseline 而非排查代码回退(先例 #6015)。

### 先例 issue(格式参考)

| Issue | 说明 |
|-------|------|
| #5694 | 标准格式正文(Wan2.2) |
| #5968 | 两个同系列模型合并一个 issue |
| #6015 | 单条数据 + 评论说明 baseline 需调整 |
| #5960 | 旧标题改标准格式 + 评论补数据 |

---

## Part 2 — Buildkite/local failed case issues

处理日报三个 **Failure analysis** 部分(Buildkite CUDA / Buildkite NPU / Local test)中的失败测试。

### 工作流

```
- [ ] 1. 解析日报,提取三个部分的全部失败行
- [ ] 2. 核实 Buildkite 失败:重试后是否仍失败(仍在跑则等待)
- [ ] 3. GitHub 查重(open + closed)
- [ ] 4. 与用户确认三类清单后执行
- [ ] 5. open issue 补评论 / 新提 issue,提交后查乱码
```

### Step 1 — 解析日报提取失败行

日报是单个大 HTML(>1MB),失败行是带 `btn-github-issue` 按钮的 `<tr>`,用 Python 正则提取:

- tr 属性:`data-report-context`(区分 CUDA/NPU/local)、`data-issue-env`(ci/local)、
  `data-buildkite-build-url`、`data-buildkite-step-url`、`data-buildkite-step-name`、`data-build-commit`
- 单元格依次:test node、log reason、analysis、log excerpt(`<pre class="log-excerpt">`,
  另有 `log-excerpt--stored` 存完整日志)
- excerpt 清洗:去 HTML 标签、`html.unescape`、压缩连续空行

**已知陷阱(均为实战踩过):**

| 陷阱 | 应对 |
|------|------|
| summary 列出的失败 step 没有对应失败行 | 通常是日志抓取被 429 限流;去 Buildkite 核实,step 可能实际是通过的(误报) |
| 报告自动 analysis 分类不可靠(gguf 配置错误被标成 timeout、subprocess 错误被标成 skip/xfail) | 以 excerpt 里的真实 traceback 为准,issue 里的 Analysis 自己写 |
| Local 部分 "Log reason" 是无关 INFO 行 | 看 raw log:`vllm-omni-kanban/data/local_nightly_raw/<最新目录>/<job>.log` |
| Local 数据可能是旧日期 | local 取自 `local_nightly_raw/` 最新目录(如 `manual_20260805`),用目录名和日志时间戳核对运行日期;若比 issue 里已有记录更旧,**不要**当"最新结果"发评论 |

### Step 2 — 核实 Buildkite 重试

Token 在环境变量 `BUILDKITE_API_TOKEN`(~/.zshrc)。API:

```
https://api.buildkite.com/v2/organizations/vllm/pipelines/{vllm-omni|vllm-omni-npu-ci}/builds/{n}
```

- jobs 数组只含每个 step 的**最新尝试**;`retries_count=1` 表示该 job 是重试。
- build `state=failing` 表示还有 job 在跑(重试中),`failed` 表示已终结。
- 判定:重试后 `state=failed` → 确认复现,可提;重试 `passed` → 偶发,不提;
  `running` → 等待(后台脚本每 2 分钟轮询,结束自动通知,不阻塞其他失败的处理)。
- 无人触发过重试(`retries_count` 为空)时,与用户确认是否手动 retry 或直接按单次失败处理。

**核对重试失败的是同一测试**——拉重试 job 日志:

```
GET .../builds/{n}/jobs/{job_id}/log.txt   (Accept: text/plain)
```

清洗 ANSI 转义(`\x1b[...m`)、`_bk;t=<毫秒>` 时间戳后 grep `short test summary`。
注意 pytest `-s` 实时输出中 `... PASSED tests/...::test_next` 的 verdict 属于**前一个**测试,
容易看串行;最终结论一律以 `short test summary info` 段为准。

一个 step 跑多个测试时,重试可能"原失败测试通过、另一个测试失败"(音频相似度类断言常见)——
这属于抖动信号,单独列出与用户讨论,不要直接归入"复现"。

### 变体流程 — 日报未生成时直连 Buildkite

日报晚点/未生成时,跳过 Step 1,直接从 Buildkite API 拿数据(其余步骤不变):

**1. 找最新 scheduled nightly**(CUDA 和 NPU 两条流水线各一个):

```
GET /v2/organizations/vllm/pipelines/{vllm-omni|vllm-omni-npu-ci}/builds?branch=main&per_page=20
→ 取 source == "schedule" 的最新一条,记下 number、commit、web_url
```

**2. 失败清单**:build 详情 jobs 数组里 `type=script` 且 `state=failed` 的(忽略 `broken`)。
没有日报的 reason/excerpt,对每个失败 job 拉 `log.txt` 自己提取 `short test summary` +
关键 traceback;issue 尾注写 "Generated from Buildkite triage of the scheduled nightly
(the HTML report was not yet generated)",commit 取 build 的 commit 字段。

**3. 识别系统性失败,避免逐个提 issue**:大量 step(尤其跨不相关 suite)在开始后几分钟内
全挂、报 `Server processes exited with code 1 before becoming ready` / `EngineCoreDeadError`
之类 → 在日志里找共同根因(典型:vllm 与 vllm-omni API 漂移导致的 ImportError/AttributeError,
grep `ImportError|ModuleNotFoundError|AttributeError`),**提一个系统性 issue** 列代表性
step 链接和两三个根因 traceback,注明重试无意义、需修镜像/pin 而非逐测试排查。

**4. 无人重试时需自己触发**(有日报的流程里通常已有人重试过):

- API 触发:`PUT .../builds/{n}/jobs/{job_id}/retry`,需要 token 有 **write_builds** scope;
  当前 `BUILDKITE_API_TOKEN` 只读会返回 403,此时把 job 链接发给用户手动点 Retry。
- 只重试有信息量的:抖动类(历史上重试通过过)和需要核实的新失败;
  确定性失败(ImportError、pydantic 校验、缺依赖、同值断言)重试无意义,直接提。
- 后台脚本轮询监控:`retries_count>=1` 出现 = 重试已开始,终态出现 = 结束,自动通知。

**5. 复判升级信号**(重试结果出来后):

| 信号 | 判定 |
|------|------|
| 断言数值两次尝试**完全相同**(bit-identical) | 确定性回归,不再是"偶发";已有 occasional issue 的要补评论纠正定性 |
| 重试失败的用例**比首次更多**(如 1 个→4 个) | 恶化趋势,即使单看每次像抖动也应提 issue,列两次尝试的完整失败清单和近几天轨迹 |
| 原失败用例重试通过、换了别的用例失败 | 抖动信号,与用户讨论;连续多天出现同类换用例失败则按恶化处理 |

### Step 3 — GitHub 查重

open + closed 一起查,关键字每轮 1~2 个、多轮尝试(全部关键字 AND 在一起会查空):

```bash
gh search issues --repo vllm-project/vllm-omni "{测试函数名}" --limit 10 --json number,title,state,updatedAt
# 依次尝试:测试函数名 → 文件名 → 报错关键句(如 "SSIM below threshold"、
# "Expected 10 completed requests"、"Unknown quantization method") → 模型名
```

| 查重结果 | 动作 |
|----------|------|
| 无相关 issue | 新提 |
| open issue 覆盖同一 test node | 补评论:本次 build 链接、commit、重试仍失败的证据;若已是当天刚更新且无新信息则不刷 |
| closed issue 覆盖同一 test node | **与用户讨论**:reopen 还是新提并引用旧 issue |
| 同 build 的失败已有人当天提过(日报值班可能重叠) | 只补重试结果,不重复提 |

查重时顺便 `gh issue view` 看正文和最近评论,确认症状是否真的相同(同一测试不同报错要区分,
如 KV-transfer 超时 vs HTTP 400)。

closed issue 处理前先看**关闭方式和时间线**(`gh api .../issues/{n}/timeline` 找 cross-referenced
的修复 PR):若由修复 PR 合入关闭、且 nightly 跑的 commit **早于**合入 commit,则本次失败属预期,
不要 reopen,等下一次 nightly 验证修复(先例:#5880 由 PR #5981 关闭当天,nightly 仍复现同值)。

### Step 4 — 与用户确认

给出三类清单:①重试仍失败→更新/新提;②重试通过或误报→不处理;③待定(closed issue、
换了测试失败的抖动、数据过期)→逐个讨论。确认后执行。

### Step 5 — 提 issue / 补评论

模板 = 日报 "Submit issue" 按钮生成的 `400-bug-report.yml` 预填页,用 `gh` 等价创建。

**标题**(来自日报内嵌 JS 的规则):

```
[Bug]: Nightly / CI failed - {test node} - {log reason}     # CUDA
[Bug][NPU]: Nightly / CI failed - {test node} - {log reason} # NPU
```

超过 220 字符截断为 217 + `...`。

**labels:** CI 失败 `bug` + `ci-failure` + `high priority`;local 失败仅 `bug`。

**正文结构**(与 Part 1 相同的三段;Describe 段内容如下):

```markdown
**Buildkite build:** {build url}
**Buildkite step:** [{step name}]({step url})

**Failure kind:** pytest FAILED / pytest ERROR
**Test node:** `{node}`

**Log reason:**
{一句报错}

**Analysis:**
{自己写:失败位置、断言内容、是否确定性(两次尝试同值→确定性回归)、可能关联的 issue/RFC}

**Retry:** the step was retried once and failed on the same test node again ([retry job]({url}), finished {UTC 时间}):

```text
FAILED {short summary 行}
```

**Error log excerpt:**

```text
{清洗后的 excerpt}
```
```

**执行要点:**

- 正文写入临时文件用 `--body-file` 提交,避免 heredoc 里反引号/引号转义问题。
- 补评论模板:build 链接 + commit + 本次现象 + 重试证据;有增量信息才写
  (如 online/offline SSIM 两次尝试完全同值→指出是确定性回归而非抖动)。
- **提交后查乱码**:拉回 title/body/labels,检查 U+FFFD、`â€`/`Ã©` 类 mojibake、
  `&amp;` 等 HTML entities、`%20` URL 编码残留,并目视 head/tail 确认完整。
- 评论发错了删除:评论 URL 尾部是 `#issuecomment-{id}`,
  `gh api -X DELETE repos/vllm-project/vllm-omni/issues/comments/{id}`,删后确认最后一条评论恢复正常。

---

## 注意事项

- 所有 `gh` 写操作(创建 issue、评论、改标题)前须经用户确认。
- commit 哈希写入正文前核对完整 40 位,避免笔误(先例:#5968 曾写错末位后修正)。
- 报告中 "Days failing" 上限显示 `3 days+`,实际连续天数看解析脚本输出的 `data-consec-days`。
