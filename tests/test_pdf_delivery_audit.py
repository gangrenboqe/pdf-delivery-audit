"""pdf-delivery-audit 的单元测试。

这个工具的价值在于「交付前拦住坏文件」，所以测试必须覆盖：
  · 纯函数（下边距改写）
  · 依赖pypdf 的取文（用**自己生成的空白 PDF**，不依赖任何私人文件）
  · 报错路径（文件不存在 / 不是 PDF）

运行：python -m unittest discover -s tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypdf

from pdf_delivery_audit import build_with_bottom_margin, extract_text


HTML_WITH_PAGE = """<!doctype html><html><head><style>
@page { size: A4; margin: 25.4mm 25.4mm 25.4mm 25.4mm; }
body { font-family: sans-serif; }
</style></head><body><h1>Resume</h1><p>Hello</p></body></html>"""


class TestBuildWithBottomMargin(unittest.TestCase):
    def test_replaces_margin(self):
        out = build_with_bottom_margin(HTML_WITH_PAGE, 10)
        self.assertIn("margin: 11mm 11mm 10mm 11mm;", out)

    def test_custom_top_and_side(self):
        out = build_with_bottom_margin(HTML_WITH_PAGE, 10, side_mm=15, top_mm=20)
        self.assertIn("margin: 20mm 15mm 10mm 15mm;", out)

    def test_body_untouched(self):
        """只该改 @page 里的 margin，正文样式不能被动。"""
        out = build_with_bottom_margin(HTML_WITH_PAGE, 10)
        self.assertIn("font-family: sans-serif;", out)

    def test_no_page_rule_is_safe(self):
        """HTML 里没有 @page 时不能崩——这是真实的边界情况。"""
        out = build_with_bottom_margin("<html><body>x</body></html>", 10)
        self.assertIn("<body>x</body>", out)

    def test_only_first_page_rule_changed(self):
        """count=1：只改第一个 @page，避免误伤后面的内容。"""
        html = HTML_WITH_PAGE + "<style>@page{margin:1mm 1mm 1mm 1mm;}</style>"
        out = build_with_bottom_margin(html, 10)
        self.assertIn("margin: 11mm 11mm 10mm 11mm;", out)
        self.assertIn("margin:1mm 1mm 1mm 1mm;", out)


class TestExtractText(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def _make_pdf(self, pages=1):
        w = pypdf.PdfWriter()
        for _ in range(pages):
            w.add_blank_page(width=595, height=842)  # A4
        p = self.dir / "t.pdf"
        with open(p, "wb") as f:
            w.write(f)
        return p

    def test_counts_pages(self):
        for n in (1, 2, 5):
            pages, text = extract_text(str(self._make_pdf(n)))
            self.assertEqual(pages, n)

    def test_blank_page_text_is_empty_not_none(self):
        """空白页应返回空字符串而不是 None——否则下游 len() 会炸。"""
        pages, text = extract_text(str(self._make_pdf(1)))
        self.assertIsInstance(text, str)

    def test_missing_file_raises(self):
        with self.assertRaises(Exception):
            extract_text(str(self.dir / "nope.pdf"))

    def test_not_a_pdf_raises(self):
        """把文本文件当 PDF 读，必须报错而不是静默返回 0 页。"""
        bad = self.dir / "bad.pdf"
        bad.write_text("this is not a pdf", encoding="utf-8")
        with self.assertRaises(Exception):
            extract_text(str(bad))


if __name__ == "__main__":
    unittest.main(verbosity=2)