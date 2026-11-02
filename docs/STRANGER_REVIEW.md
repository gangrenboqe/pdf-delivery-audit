# 陌生人复验记录（35 号工单 · P4 pdf-delivery-audit）

> 复验日期：2026-11-02 · 复验人：技术线（Trae）· 方法：真 clone（SSH）+ 工作区实跑体检

## 结果

**体检一次跑通（真实 Chrome 打印引擎 + pypdf，全程离线）；真 clone 抓到并修正一个 README 数字失实。**

## 工作区实跑（demo 内容本体）

```
python pdf_delivery_audit.py samples/resume_sample.html --must-have 张三 --must-have GitHub
[页数]      1 页 ／ 底部余量 79 mm        ✅
[机器可读]  可提取字符数 = 394（阈值 300） ✅
[关键字段]  全部命中 ✅
结论：✅ 可以交付（退出码 0）
```

- 样例输入：`samples/resume_sample.html`（**完全虚构的合成简历**，姓名/邮箱/GitHub 全为示例占位，无真实个人信息）
- 运行输出原文：[docs/audit_run.txt](audit_run.txt)；体检产物（真实导出的 PDF）：[docs/resume_sample_output.pdf](resume_sample_output.pdf)——**打开这份 PDF 能选中文字**，正是"机器能读"的直接证据

## 真 clone（SSH）原文

```
git clone git@github.com:gangrenboqe/pdf-delivery-audit.git
Cloning into 'pdf-delivery-audit'...
clone 后目录名: pdf-delivery-audit   ✓ 与 README 的 cd 一致
python -m unittest discover -s tests → Ran 9 tests ... OK（HEAD 自带测试，离线）
```

## 复验中修掉的问题

- `.gitignore` 补 `samples/*.pdf`：体检运行会在 samples/ 旁重新生成同名 PDF（运行产物，不进仓）；
  证据快照放 docs/（进仓）——与 P2/P3 的 out/ 处理口径一致。

## 待推送后复验的部分

`samples/resume_sample.html`、docs/ 证据与 README 顶部「三步跑起来」**尚未推送**。
推送后照三步可完整复验：唯一前置是本机装有 Chrome/Edge（打印引擎，脚本找不到会明确报错而非静默失败），
依赖只有 `pip install pypdf`。

## 复验环境

- Windows 11，Python 3.11，pypdf 6.7.5，本机 Chrome，SSH 认证，未联网调用任何 API
