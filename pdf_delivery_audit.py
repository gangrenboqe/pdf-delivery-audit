#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_delivery_audit —— 交付前的 PDF 体检器

它回答两个问题，缺一不可：

  1) 页数     —— 用真实打印引擎（Chrome / Edge 无头模式）导出 PDF，
                 再用**二分查找**试探「下边距加到多少毫米才会溢出到第二页」，
                 得出真实页数与底部余量（mm）。
  2) 机器可读 —— 抽 PDF 的文字层，数一数到底能提取出多少个字符。

为什么第 2 条是硬性的（这是一个真实发生过的教训）：
  我交付过一份 PDF 投递件，页面上文字、排版**看着完全正常**，
  但它被导出成了上千个矢量图形：0 个嵌入字体、0 个可提取字符。
  人眼读得懂，机器的简历解析系统（ATS, Applicant Tracking System）
  读它等于读一张白纸。

**所以：交付前不仅要确认"看着对"，还要确认"机器能读"。**

为什么用二分而不是估算：
  我按字宽算过一次排版高度，比真实排版偏了 18mm（约 4 行），足够翻页。
  估算不算数 —— 能用真引擎就别用估算。

用法：
    python pdf_delivery_audit.py resume.html
    python pdf_delivery_audit.py resume.html --must-have github.com --must-have "@"
    python pdf_delivery_audit.py doc.html --min-chars 500 --bottom 10

退出码：0 = 通过；1 = 未通过（可直接拿来当交付门禁 / CI 关卡）
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

try:
    import pypdf
except ImportError:
    sys.stderr.write("缺少依赖 pypdf，请先执行：pip install -r requirements.txt\n")
    sys.exit(2)


# --------------------------------------------------------------------------
# 1. 找打印引擎（浏览器）
# --------------------------------------------------------------------------
CANDIDATE_COMMANDS = ["chrome", "msedge", "google-chrome", "chromium"]
CANDIDATE_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser() -> str:
    """按优先级找：环境变量 → PATH → 常见安装路径。找不到就明确报错。"""
    env_path = os.environ.get("CHROME_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    for cmd in CANDIDATE_COMMANDS:
        found = shutil.which(cmd)
        if found:
            return found
    for path in CANDIDATE_PATHS:
        if os.path.exists(path):
            return path
    sys.stderr.write(
        "找不到 Chrome / Edge。请安装，或设置环境变量 CHROME_PATH 指向可执行文件。\n"
    )
    sys.exit(2)


# --------------------------------------------------------------------------
# 2. 导出与测量
# --------------------------------------------------------------------------
def build_with_bottom_margin(html: str, bottom_mm: int,
                             side_mm: int = 11, top_mm: int = 11) -> str:
    """把 @page { margin: ... } 的下边距改成指定毫米数，用于二分试探。"""
    def rep(match):
        css = match.group(0)
        return re.sub(
            r"margin\s*:\s*([^;]+);",
            "margin: %dmm %dmm %dmm %dmm;" % (top_mm, side_mm, bottom_mm, side_mm),
            css,
        )
    return re.sub(r"@page\s*\{[^}]*\}", rep, html, count=1)


def export_pdf(browser: str, html_path: str, out_path: str, timeout: int = 120) -> str:
    url = "file:///" + urllib.parse.quote(os.path.abspath(html_path).replace("\\", "/"))
    if os.path.exists(out_path):
        os.remove(out_path)
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         "--print-to-pdf=" + out_path, url],
        capture_output=True, timeout=timeout,
    )
    if not os.path.exists(out_path):
        raise RuntimeError("打印引擎没能产出 PDF：%s" % out_path)
    return out_path


def count_pages(browser: str, html_path: str, bottom_mm: int, timeout: int = 120) -> int:
    """用指定下边距导出一次，只看页数。"""
    html = open(html_path, encoding="utf-8").read()
    tmp_html = html_path + ".__probe.html"
    tmp_pdf = html_path + ".__probe.pdf"
    open(tmp_html, "w", encoding="utf-8").write(build_with_bottom_margin(html, bottom_mm))
    try:
        export_pdf(browser, tmp_html, tmp_pdf, timeout)
        return len(pypdf.PdfReader(tmp_pdf).pages)
    finally:
        for f in (tmp_html, tmp_pdf):
            if os.path.exists(f):
                os.remove(f)


def binary_search_slack(browser: str, html_path: str, base_mm: int, hi_mm: int,
                        target_pages: int, timeout: int = 120) -> tuple[int, int]:
    """
    二分查找：在「不超出目标页数」的前提下，底部最多还能留多少 mm。
    返回 (可容纳的最大下边距, 余量 mm)
    """
    lo, hi = base_mm, hi_mm
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if count_pages(browser, html_path, mid, timeout) <= target_pages:
            lo = mid
        else:
            hi = mid - 1
    return lo, lo - base_mm


def extract_text(pdf_path: str) -> tuple[int, str]:
    reader = pypdf.PdfReader(pdf_path)
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return len(reader.pages), text


# --------------------------------------------------------------------------
# 3. 主流程
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="交付前的 PDF 体检：页数 + 底部余量 + 机器可读性 + 关键字段"
    )
    ap.add_argument("html", help="待体检的 HTML 文件")
    ap.add_argument("--must-have", action="append", default=[],
                    help="必须出现在文字层里的关键词，可重复传（例：--must-have github.com）")
    ap.add_argument("--must-have-any", action="append", default=[],
                    help="至少要命中其中一个的关键词组，可重复传")
    ap.add_argument("--bottom", type=int, default=11, help="原始下边距（mm），默认 11")
    ap.add_argument("--max-bottom", type=int, default=90, help="二分上界（mm），默认 90")
    ap.add_argument("--target-pages", type=int, default=1, help="期望页数，默认 1")
    ap.add_argument("--min-slack", type=int, default=8, help="最小可接受底部余量（mm），默认 8")
    ap.add_argument("--min-chars", type=int, default=300,
                    help="文字层最少可提取字符数，默认 300（低于此值视为 ATS 读不出）")
    ap.add_argument("--no-export", action="store_true", help="只体检，不保留投递用 PDF")
    args = ap.parse_args()

    path = os.path.abspath(args.html)
    if not os.path.exists(path):
        sys.stderr.write("文件不存在：%s\n" % path)
        return 2

    browser = find_browser()
    name = os.path.basename(path)

    # 1) 用原始参数导出真正带文字层的 PDF（这份就是可投递件）
    out_pdf = os.path.splitext(path)[0] + ".pdf"
    export_pdf(browser, path, out_pdf)
    pages, text = extract_text(out_pdf)
    n_chars = len(text.strip())

    # 2) 二分试探真实余量
    _, slack = binary_search_slack(browser, path, args.bottom, args.max_bottom,
                                   args.target_pages)

    print("=" * 60)
    print("PDF 交付体检：%s" % name)
    print("=" * 60)
    print("[页数]      %d 页 ／ 底部余量 %d mm" % (pages, slack))

    ok = True

    if pages > args.target_pages:
        print("            ❌ 超出目标页数（目标 %d 页）" % args.target_pages)
        ok = False
    elif slack < args.min_slack:
        print("            ⚠️ 余量不足 %dmm，换浏览器 / 开页眉页脚可能翻页" % args.min_slack)
        ok = False
    else:
        print("            ✅ 页数 OK")

    print("[机器可读]  可提取字符数 = %d（阈值 %d）" % (n_chars, args.min_chars))
    if n_chars < args.min_chars:
        print("            🔴 几乎没有文字层 —— 机器读不到，等同废纸")
        ok = False
    else:
        print("            ✅ 文字层 OK")

    if args.must_have:
        missing = [k for k in args.must_have if k not in text]
        print("[关键字段]  %s" % ("全部命中 ✅" if not missing
                                else "缺失 → " + ", ".join(missing)))
        if missing:
            ok = False

    if args.must_have_any:
        hit = [k for k in args.must_have_any if k in text]
        print("[任选字段]  %s" % ("命中「%s」✅" % "、".join(hit) if hit
                                else "🔴 一组都没命中"))
        if not hit:
            ok = False

    print("-" * 60)
    print("结论：%s" % ("✅ 可以交付" if ok else "🔴 还不能交付，先修上面标红/黄的项"))
    if args.no_export:
        os.remove(out_pdf)
        print("（已按 --no-export 删除导出的 PDF）")
    else:
        print("投递件已生成：%s" % out_pdf)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
