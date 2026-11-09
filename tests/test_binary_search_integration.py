"""二分查找 + 真实打印引擎的集成测试（43-batch 关键路径补测）。

count_pages / binary_search_slack 依赖 Chrome/Edge 无头导出，此前零测试——
这是「底部余量」结论的生产路径，若悄悄坏掉（页数恒为 1、二分区间错），
体检报告会给出假余量而不报错。需要本机有 Chrome/Edge；没有就跳过（环境门控，
不是为了让测试变绿——有浏览器时它一定真跑）。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pdf_delivery_audit import binary_search_slack, count_pages, find_browser  # noqa: E402

ONE_PAGE_HTML = """<!doctype html><html><head><style>
@page {{ margin: 11mm 11mm 11mm 11mm; }}
body {{ font-size: 10pt; }}
</style></head><body>
<h1>简历标题</h1>
<p>{}</p>
</body></html>""".format("这是一段用于占位的正文。" * 30)

BROWSER = None
try:
    BROWSER = find_browser()
except SystemExit:
    BROWSER = None  # 本机没有 Chrome/Edge


@unittest.skipIf(BROWSER is None, "本机没有 Chrome/Edge，集成测试跳过（有浏览器时真跑）")
class BinarySearchIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.html_path = Path(cls.tmp.name) / "sample.html"
        cls.html_path.write_text(ONE_PAGE_HTML, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_count_pages_one_page(self):
        """小内容 + 任意合理下边距 → 必须是 1 页（打印引擎真的在跑）。"""
        n = count_pages(BROWSER, str(self.html_path), 11)
        self.assertEqual(n, 1)

    def test_binary_search_returns_consistent_slack(self):
        """二分结果必须满足：lo∈[base,hi]、余量=lo-base、且余量处页数仍达标。"""
        base, hi = 5, 40
        lo, slack = binary_search_slack(BROWSER, str(self.html_path), base, hi, 1)
        self.assertTrue(base <= lo <= hi)
        self.assertEqual(slack, lo - base)
        self.assertGreaterEqual(count_pages(BROWSER, str(self.html_path), lo), 1)
        # 内容很小：即使顶到上界 hi 也应是 1 页 → 余量应打满
        self.assertEqual((lo, slack), (hi, hi - base))


if __name__ == "__main__":
    unittest.main()
