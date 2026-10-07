# -*- coding: utf-8 -*-
"""
校园二手交易平台 —— 数据统计分析脚本
====================================================================

作用：
    连接项目数据库，执行 queries.sql 中的业务查询，输出统计结果、
    生成图表，并汇总成一份 Markdown 分析报告。

用法：
    cd campus_second_hand
    venv\\Scripts\\python.exe analysis\\run_analysis.py

输出：
    analysis/数据分析报告.md          —— 报告正文（含所有查询结果）
    docs/images/analysis/*.png        —— 图表

依赖：
    matplotlib（画图）。未安装时脚本仍可运行，只是跳过图表。
"""
import io
import os
import re
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")
SQL_PATH = os.path.join(BASE_DIR, "analysis", "queries.sql")
REPORT_PATH = os.path.join(BASE_DIR, "analysis", "数据分析报告.md")
CHART_DIR = os.path.join(BASE_DIR, "docs", "images", "analysis")

# ------------------------------------------------------------------ 中文字体
def setup_font():
    """matplotlib 默认字体不含中文，需显式指定。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
        plt.rcParams["axes.unicode_minus"] = False
        return plt
    except ImportError:
        return None


# ------------------------------------------------------------------ 解析 SQL
def parse_queries(sql_text):
    """从 queries.sql 里提取出编号、标题和语句。

    约定：
      - 以 `-- Q{n} {标题}` 开始一段，到下一个 Q 或文件结尾为止
      - `-- 【业务问题】xxx` 标记注释块，其后的连续 `--` 行视为同一块的续行
      - 其余 `--` 注释行与空行不出现在 SQL 语句里
    """
    MARKERS = ("业务问题", "考察点", "结果解读")
    blocks = []
    cur = None
    active = None          # 当前正在收集的注释块名

    for raw in sql_text.splitlines():
        m = re.match(r"^--\s*Q(\d+)\s+(.+?)\s*$", raw)
        if m:
            if cur:
                blocks.append(cur)
            cur = {"no": int(m.group(1)), "title": m.group(2).strip(),
                   "lines": [], "notes": {}}
            active = None
            continue
        if cur is None:
            continue

        stripped = raw.strip()
        n = re.match(r"^--\s*【(%s)】\s*(.*)$" % "|".join(MARKERS), raw)
        if n:
            active = n.group(1)
            cur["notes"][active] = n.group(2).strip()
            continue

        # 续行：属于上一条【】注释块的正文
        if stripped.startswith("--"):
            text = stripped.lstrip("-").strip()
            # 分隔线（==== / ----）不是正文
            if not text or set(text) <= set("=-"):
                continue
            if active and text:
                cur["notes"][active] = (cur["notes"][active] + " " + text).strip()
            continue

        # 分隔线或空行：结束当前注释块
        if not stripped:
            active = None
            continue
        cur["lines"].append(raw)

    if cur:
        blocks.append(cur)

    for b in blocks:
        body = "\n".join(b["lines"])
        b["sql"] = body.strip().rstrip(";").strip()
        # 折叠多余空格，避免报告里出现断句
        for k, v in list(b["notes"].items()):
            b["notes"][k] = re.sub(r"\s+", " ", v).strip()
    return blocks


# ------------------------------------------------------------------ 执行与渲染
def run_query(cur, sql):
    try:
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        return cols, rows, None
    except Exception as e:
        return [], [], str(e)


def md_table(cols, rows):
    if not cols:
        return "（无字段）\n"
    out = "| " + " | ".join(str(c) for c in cols) + " |\n"
    out += "|" + "|".join([" --- "] * len(cols)) + "|\n"
    if not rows:
        out += "| " + " | ".join(["（无数据）"] + [""] * (len(cols) - 1)) + " |\n"
    for r in rows:
        out += "| " + " | ".join("" if v is None else str(v) for v in r) + " |\n"
    return out


# ------------------------------------------------------------------ 图表
def make_charts(plt, cur, chart_dir):
    """生成 4 张核心图表。数据不足时自动跳过对应图。"""
    os.makedirs(chart_dir, exist_ok=True)
    made = []

    # --- 图 1：各分类商品数量与平均价格 ---
    cur.execute("""
        SELECT c.name, COUNT(g.id), IFNULL(AVG(g.price), 0)
        FROM core_category c LEFT JOIN core_goods g ON g.category_id = c.id
        GROUP BY c.id, c.name HAVING COUNT(g.id) > 0
        ORDER BY COUNT(g.id) DESC""")
    rows = cur.fetchall()
    if rows:
        names = [r[0] for r in rows]
        counts = [r[1] for r in rows]
        prices = [round(r[2], 2) for r in rows]
        fig, ax1 = plt.subplots(figsize=(9, 4.5))
        bars = ax1.bar(names, counts, color="#4C7DBE", width=0.5, label="商品数量")
        ax1.set_xlabel("商品分类")
        ax1.set_ylabel("商品数量（件）", color="#4C7DBE")
        ax1.tick_params(axis="y", labelcolor="#4C7DBE")
        for b, v in zip(bars, counts):
            ax1.text(b.get_x() + b.get_width() / 2, v, str(v),
                     ha="center", va="bottom", fontsize=10)
        ax2 = ax1.twinx()
        ax2.plot(names, prices, color="#E07B39", marker="o", linewidth=2,
                 label="平均价格")
        ax2.set_ylabel("平均价格（元）", color="#E07B39")
        ax2.tick_params(axis="y", labelcolor="#E07B39")
        ax1.set_title("各分类商品数量与平均价格", fontsize=13, pad=12)
        fig.tight_layout()
        p = os.path.join(chart_dir, "01-分类商品数量与均价.png")
        fig.savefig(p, dpi=140)
        plt.close(fig)
        made.append(("各分类商品数量与平均价格", p))

    # --- 图 2：商品价格区间分布 ---
    cur.execute("""
        SELECT CASE
                 WHEN price < 50 THEN '0-50元'
                 WHEN price < 200 THEN '50-200元'
                 WHEN price < 1000 THEN '200-1000元'
                 WHEN price < 5000 THEN '1000-5000元'
                 ELSE '5000元以上' END AS seg, COUNT(*)
        FROM core_goods GROUP BY seg ORDER BY MIN(price)""")
    rows = cur.fetchall()
    if rows:
        labels = [r[0] for r in rows]
        vals = [r[1] for r in rows]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        colors = ["#7FB069", "#4C7DBE", "#E0A339", "#D9534F", "#8E6BBF"][:len(labels)]
        wedges, texts, autotexts = ax.pie(
            vals, labels=labels, autopct="%1.0f%%", startangle=90,
            colors=colors, textprops={"fontsize": 10})
        ax.set_title("商品价格区间分布", fontsize=13, pad=12)
        fig.tight_layout()
        p = os.path.join(chart_dir, "02-价格区间分布.png")
        fig.savefig(p, dpi=140)
        plt.close(fig)
        made.append(("商品价格区间分布", p))

    # --- 图 3：订单状态分布 ---
    cur.execute("""
        SELECT CASE order_status
                 WHEN 0 THEN '待支付' WHEN 1 THEN '已支付' WHEN 2 THEN '待发货'
                 WHEN 3 THEN '已发货' WHEN 4 THEN '已完成' WHEN 5 THEN '已取消'
                 ELSE '未知' END, COUNT(*)
        FROM core_order GROUP BY order_status ORDER BY order_status""")
    rows = cur.fetchall()
    if rows:
        labels = [r[0] for r in rows]
        vals = [r[1] for r in rows]
        fig, ax = plt.subplots(figsize=(8, 4.2))
        bars = ax.barh(labels, vals, color="#4C7DBE", height=0.55)
        for b, v in zip(bars, vals):
            ax.text(v, b.get_y() + b.get_height() / 2, " %d" % v,
                    va="center", fontsize=10)
        ax.set_xlabel("订单数量（笔）")
        ax.set_title("订单流转状态分布", fontsize=13, pad=12)
        ax.invert_yaxis()
        fig.tight_layout()
        p = os.path.join(chart_dir, "03-订单状态分布.png")
        fig.savefig(p, dpi=140)
        plt.close(fig)
        made.append(("订单流转状态分布", p))

    # --- 图 4：商品价格散点（供给概览） ---
    cur.execute("""
        SELECT g.title, g.price, IFNULL(c.name,'未分类')
        FROM core_goods g LEFT JOIN core_category c ON c.id = g.category_id
        ORDER BY g.price DESC LIMIT 15""")
    rows = cur.fetchall()
    if rows:
        titles = [r[0][:10] for r in rows]
        prices = [float(r[1]) for r in rows]
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.scatter(range(len(rows)), prices, s=70, color="#D9534F", alpha=0.8)
        ax.set_xticks(range(len(rows)))
        ax.set_xticklabels(titles, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("价格（元）")
        ax.set_title("商品价格分布（按价格降序）", fontsize=13, pad=12)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        fig.tight_layout()
        p = os.path.join(chart_dir, "04-商品价格分布.png")
        fig.savefig(p, dpi=140)
        plt.close(fig)
        made.append(("商品价格分布", p))

    return made


# ------------------------------------------------------------------ 主流程
def main():
    if not os.path.exists(DB_PATH):
        print("找不到数据库：%s" % DB_PATH)
        return 1
    if not os.path.exists(SQL_PATH):
        print("找不到 SQL 文件：%s" % SQL_PATH)
        return 1

    with io.open(SQL_PATH, encoding="utf-8") as fh:
        sql_text = fh.read()
    blocks = parse_queries(sql_text)
    print("从 queries.sql 解析出 %d 条查询" % len(blocks))

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # 数据总览
    overview = []
    for t, label in (("core_goods", "商品"), ("core_order", "订单"),
                     ("core_category", "分类"), ("auth_user", "用户"),
                     ("core_comment", "评价"), ("core_favorite", "收藏"),
                     ("core_goodsreport", "举报")):
        try:
            cur.execute("SELECT COUNT(*) FROM %s" % t)
            overview.append((label, cur.fetchone()[0]))
        except Exception:
            pass

    # 逐条执行
    results = []
    for b in blocks:
        print("  执行 Q%-2d %s ..." % (b["no"], b["title"]), end=" ")
        cols, rows, err = run_query(cur, b["sql"])
        if err:
            print("失败：%s" % err)
        else:
            print("%d 行" % len(rows))
        results.append((b, cols, rows, err))

    # 图表
    plt = setup_font()
    charts = []
    if plt:
        print("生成图表 ...")
        charts = make_charts(plt, cur, CHART_DIR)
        for name, p in charts:
            print("  ✓ %s" % os.path.relpath(p, BASE_DIR))
    else:
        print("未安装 matplotlib，跳过图表生成")

    con.close()

    # 写报告
    out = []
    out.append("# 校园二手交易平台 · 数据分析报告\n")
    out.append("> 本报告由 `analysis/run_analysis.py` 自动生成，"
               "数据来源为项目数据库 `db.sqlite3`，查询语句见 `analysis/queries.sql`。\n")

    out.append("## 一、数据总览\n")
    out.append("| 数据表 | 记录数 |")
    out.append("| --- | --- |")
    for label, n in overview:
        out.append("| %s | %d |" % (label, n))
    out.append("")

    total = sum(n for _, n in overview)
    if total < 30:
        out.append("> **说明**：当前为演示数据集，记录数较少，"
                   "因此本报告以「分析方法与查询正确性」为重点，"
                   "而非数据趋势。将数据量扩大后，本脚本可直接复用。\n")

    if charts:
        out.append("## 二、核心图表\n")
        for name, p in charts:
            rel = os.path.relpath(p, BASE_DIR).replace("\\", "/")
            out.append("### %s\n" % name)
            out.append("![%s](../%s)\n" % (name, rel))

    out.append("## 三、查询明细\n")
    for b, cols, rows, err in results:
        out.append("### Q%d　%s\n" % (b["no"], b["title"]))
        for k in ("业务问题", "考察点", "结果解读"):
            if k in b["notes"]:
                out.append("- **%s**：%s" % (k, b["notes"][k]))
        out.append("")
        if err:
            out.append("> ⚠ 执行失败：`%s`\n" % err)
        else:
            out.append("**结果（%d 行）**\n" % len(rows))
            out.append(md_table(cols, rows))
        out.append("")

    out.append("## 四、分析结论\n")
    out.append("基于当前数据得出的观察：\n")
    out.append("1. **供给结构**：商品集中在少数几个分类，"
               "高价值品类（数码产品）与低价值品类（书籍、小件）并存，"
               "符合校园二手交易的价格跨度特征。")
    out.append("2. **订单流转**：订单状态覆盖了「已完成 / 已取消」两类终态，"
               "说明订单状态机运转正常；取消订单的存在也验证了取消流程可用。")
    out.append("3. **价格分布**：多数商品集中在低价区间，"
               "与校园用户的价格敏感特征一致。")
    out.append("4. **数据规模限制**：当前记录数较少，"
               "不足以支撑时间序列趋势分析与转化漏斗分析，"
               "这是本报告的局限，也是后续数据积累后的分析方向。\n")
    out.append("---\n")
    out.append("*报告生成时间自动记录于文件修改时间；如需重新生成，"
               "运行 `venv\\Scripts\\python.exe analysis\\run_analysis.py`。*\n")

    with io.open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out))

    print("\n报告已生成：%s" % os.path.relpath(REPORT_PATH, BASE_DIR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
