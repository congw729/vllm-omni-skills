#!/usr/bin/env python3
"""解析 vLLM-Omni nightly HTML 日报的 "All major regressions" 表。

按模型聚合输出回退行(连续天数、test、metric、幅度、config),
并输出日报中的 vllm 版本与 vllm-omni build commit,供提 issue 时引用。

用法:
    python parse_regressions.py                     # 自动取 kanban 下最新日报
    python parse_regressions.py --report <html>    # 指定日报文件
    python parse_regressions.py --model qwen       # 只看匹配关键字的模型(输出 markdown 行)
"""

import argparse
import html
import re
from collections import defaultdict
from pathlib import Path

DEFAULT_REPORT_DIR = Path("/Users/congwang/Documents/GitHub/vllm-omni-kanban/data/nightly_test_report")

ROW_PATTERN = re.compile(
    r'<tr class="summary-row--fail[^"]*"[^>]*' r'data-model="([^"]+)" data-hardware="([^"]+)" data-consec-days="(\d+)"[^>]*>(.*?)</tr>',
    re.S,
)


def find_latest_report(report_dir: Path) -> Path:
    reports = sorted(report_dir.glob("nightly-report-buildkite-latest-*.html"))
    if not reports:
        raise FileNotFoundError(f"no nightly report found in {report_dir}")
    return reports[-1]


def parse_rows(text: str) -> list:
    """返回 (model, hardware, consec_days, td 列表) 的列表。

    td 列顺序: Source, Model, Hardware, Type, Config, Test, Metric,
    latest, baseline, vs baseline, Status, Days failing
    """
    start = text.find("All major regressions")
    end = text.find("</table>", start)
    rows = []
    for model, hardware, days, body in ROW_PATTERN.findall(text[start:end]):
        tds = [html.unescape(re.sub(r"<[^>]+>", "", td)).strip() for td in re.findall(r"<td[^>]*>(.*?)</td>", body, re.S)]
        rows.append((model, hardware, int(days), tds))
    return rows


def print_version_info(text: str) -> None:
    commit = re.search(r'data-build-commit="([0-9a-f]+)"', text)
    vllm = re.search(r"vLLM version[ :]*([0-9][^<&\s]*)", text)
    print(f"\nbuild commit (short): {commit.group(1) if commit else '?'}")
    print(f"vllm version: {vllm.group(1) if vllm else '?'}")
    print("完整哈希: gh api repos/vllm-project/vllm-omni/commits/{短哈希} --jq .sha")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=None, help="日报 HTML 路径,缺省取最新")
    parser.add_argument("--model", default=None, help="模型名关键字过滤,输出可直接粘贴的 markdown 行")
    args = parser.parse_args()

    report = args.report or find_latest_report(DEFAULT_REPORT_DIR)
    print(f"report: {report}")
    text = report.read_text(encoding="utf-8")
    rows = parse_rows(text)
    print(f"total regression rows: {len(rows)}")

    if args.model:
        # 过滤模式:输出 issue 正文可直接使用的 markdown 表格行
        keyword = args.model.lower()
        for _, _, _, tds in rows:
            if keyword in tds[1].lower():
                print(" | ".join(tds))
        print_version_info(text)
        return

    # 聚合模式:按模型分组,便于筛选 >=3 天的候选
    grouped = defaultdict(list)
    for model, hardware, days, tds in rows:
        grouped[(model, hardware)].append((days, tds))
    for (model, hardware), items in sorted(grouped.items(), key=lambda kv: -max(day for day, _ in kv[1])):
        max_days = max(day for day, _ in items)
        flag = "  <-- >=3d 候选" if max_days >= 3 else ""
        print(f"\n=== {model} [{hardware}]  max consec days={max_days}  rows={len(items)}{flag}")
        for days, tds in sorted(items, key=lambda x: -x[0]):
            # tds: [Source, Model, Hardware, Type, Config, Test, Metric, latest, baseline, vs, Status, Days]
            print(f"  {days}d({tds[11]})  {tds[5]}  {tds[6]}  {tds[9]}  ({tds[4]})")

    print_version_info(text)


if __name__ == "__main__":
    main()
