# pdf-delivery-audit —— 交付前的 PDF 体检器

[![tests](https://github.com/gangrenboqe/pdf-delivery-audit/actions/workflows/test.yml/badge.svg)](https://github.com/gangrenboqe/pdf-delivery-audit/actions/workflows/test.yml)

> 一句话：**把「看着是对的」变成「机器验过是对的」。**
> 任何要交给第三方系统处理的东西（简历 PDF、导出件、上传件），
> 导出完自动体检：几页、还剩多少余量、**机器能不能读出字**。

---

## 三步跑起来（不需要联网、不需要 key；需要本机装有 Chrome 或 Edge）

```bash
git clone https://github.com/gangrenboqe/pdf-delivery-audit.git && cd pdf-delivery-audit
pip install -r requirements.txt          # 唯一依赖 pypdf（读 PDF 页数与文字层）
python pdf_delivery_audit.py samples/resume_sample.html --must-have 张三 --must-have GitHub
# → 真实打印引擎导出 PDF 并体检：页数 / 底部余量 / 可提取字符 / 关键字段，结论"可以交付"
#   真实运行输出见 docs/audit_run.txt，体检产物样例见 docs/resume_sample_output.pdf
```

> `samples/resume_sample.html` 是**完全虚构的合成简历**（无任何真实个人信息）。
> 退出码 0 = 通过、1 = 未通过——可以直接当交付门禁或 CI 关卡。
> 陌生人复验记录见 [docs/STRANGER_REVIEW.md](docs/STRANGER_REVIEW.md)。

---

## 它解决什么

我交付过一份 PDF 投递件，页面上文字和排版**看着完全正常**，
但它被导出成了上千个矢量图形：**0 个嵌入字体、0 个可提取字符**。
人眼读得懂；机器的简历解析系统（**ATS**, Applicant Tracking System，企业用来自动读取简历的系统）
读它，等于读一张白纸。

**教训：交付前不仅要确认"看着对"，还要确认"机器能读"。**
这个脚本就是把这条教训固化成每次交付前的自动检查。

第二个坑是我按字宽**估算**过一次排版高度，比真实排版偏了 18mm（约 4 行），足够翻页。
所以这里不用估算——用真实打印引擎 + 二分查找试出真实值。

---

## 迭代记录

> 这个仓库不是一次写完的。下面是真实发生过的几次「发现不对 → 改」的记录，
> 保留它们是因为：**一次失败后的归因，比十次顺利的提交更说明问题。**

### 起点是一次真实损失，不是一个好点子

这个工具的诞生顺序是：**先有损失，后有工具。**
一份页面排版完全正常的 PDF 交了出去，后来才发现它是被"另存为 PDF"打平成图形的——
**0 个嵌入字体、0 个可提取字符**（就是上一节写的那个事故）。
人眼看它是合格的，机器读它是白纸。

第一次补救很朴素：以后交 PDF 前手动复制粘贴检查一下。
但"手动检查"依赖记性和心情，于是把它写成了程序：页数二分、文字层抽查、关键字段核对，
并把**可提取字符 < 300 判废**定成硬线（即下文 `--min-chars` 的默认值）。

现在它是所有 PDF 交付前的固定步骤——包括当初那份出事的文件改版后，
也是先用它验过才交的。**损失已经发生，能做的是让同类损失不再发生。**

### 导出命令上的两个实测坑

1. **必须用 Chrome 无头模式 `--print-to-pdf` 导出**——这条路导出的 PDF 带真实文字层；
   浏览器手动"打印/另存"会把页面打平，这正是起点那次事故的成因。
2. **`--headless=new` 参数在本机实测不生成文件，必须用 `--headless`**——
   这个差异是跑出来的，不是文档写的；换机器/换版本请重验。

> 本节初稿由 AI 助手从提交历史中整理。按"写的人不审自己"的规矩，
> 它会先经另一位独立 AI 助手复核，再由设计者推送发布。

---

## 它检查什么

| 检查项 | 怎么做 | 判据 |
|---|---|---|
| 页数 | 真实打印引擎导出 PDF | 超出目标页数就判失败 |
| 底部余量 | **二分查找**试探「下边距加到多少 mm 才会翻页」 | 余量 < 8mm 判失败 |
| 机器可读性 | 抽 PDF 文字层，数可提取字符 | < 300 字符判失败（机器读不出） |
| 关键字段 | 在文字层里搜关键词 | 缺一个就判失败 |

退出码 `0` = 通过，`1` = 未通过 → **可以直接拿去当交付门禁或 CI 关卡**。

---

## 怎么用

```bash
pip install -r requirements.txt

python pdf_delivery_audit.py resume.html
python pdf_delivery_audit.py resume.html --must-have github.com --must-have "@"
python pdf_delivery_audit.py doc.html --min-chars 500 --target-pages 2
```

打印引擎（浏览器）按这个顺序找：环境变量 `CHROME_PATH` → 系统 PATH 里的
`chrome` / `msedge` / `chromium` → 常见安装路径。找不到会明确报错，不会静默失败。

常用参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--must-have` | 无 | 文字层里必须出现的关键词，可重复传 |
| `--must-have-any` | 无 | 至少要命中其中一个，可重复传 |
| `--target-pages` | 1 | 期望页数 |
| `--min-slack` | 8 | 最小可接受底部余量（mm） |
| `--min-chars` | 300 | 文字层最少可提取字符数 |
| `--bottom` / `--max-bottom` | 11 / 90 | 二分的下界与上界（mm） |
| `--no-export` | 关 | 只体检，不保留导出的 PDF |

---

## 依赖

只有一个：**`pypdf`**（读 PDF 页数与文字层）。
打印用的是本机已装的 Chrome / Edge，不需要额外下载。

> 为什么其它工具零依赖、这里有一个破例：PDF 的页数与文字层要解析压缩流和字体表，标准库做不到——这是唯一的破例。

---

## 设计上值得一提的三点

1. **不估算，用真引擎 + 二分。**
   排版高度只能靠真实打印引擎量出来；余量是多少页翻页，用二分试，比线性扫快得多。
2. **把主观判断转成可测判据。**
   "看着还行吗"没法自动判；"可提取字符 ≥ 300、余量 ≥ 8mm"可以。
3. **跨进程调用外部程序。**
   用 `subprocess` 驱动浏览器命令行，把浏览器的打印能力当成一个可复用的函数。

---

### 五分钟复现（从 clone 到看到效果）

```bash
git clone https://github.com/gangrenboqe/pdf-delivery-audit.git && cd pdf-delivery-audit
pip install -r requirements.txt            # 唯一依赖 pypdf；本机需装有 Chrome/Edge
python -m unittest discover -s tests       # 11 项（其中 2 项集成测试会真调浏览器无头导出）
python -c "open('sample.html','w',encoding='utf-8').write('<style>@page{margin:11mm}</style><body><h1>样例</h1><p>'+('占位正文。'*200)+'</p></body>')"
python pdf_delivery_audit.py sample.html   # → 体检报告：页数 / 底部余量 / 可提取字符 / 结论
```
（本机 Chrome + Python 3.11 实测：sample.html → 1 页、余量 79mm、可提取字符 1025、结论「可以交付」、退出码 0。）

## 已知边界（如实写）

- 只验证**本机**打印效果。不同浏览器 / 不同版本打印结果会有差异，
  换环境请重跑（这也是为什么余量阈值设成 8mm 而不是 0）。
- 二分每次都要真的导出一次 PDF，页数多时会慢（每次约 1-2 秒，7 次左右收敛）。
- 不做内容校对，只做结构与可读性体检。

## 许可证

自 2026-11-13 起的版本适用 [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)：可自由用于个人学习、研究、试验与非商业用途，**不得用于商业目的**。此前发布的版本适用 MIT。

Required Notice: Copyright 2026 谢一竹 (https://github.com/gangrenboqe)
