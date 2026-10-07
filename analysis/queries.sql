-- ============================================================================
--  校园二手交易平台 —— 业务分析 SQL 查询集
-- ----------------------------------------------------------------------------
--  说明：本项目使用 SQLite，以下查询针对 Django 自动生成的表名：
--        core_goods / core_order / core_category / core_comment / core_favorite
--        core_goodsreport / core_userprofile / auth_user（Django 自带用户表）
--        注意：用户表是 auth_user（Django 内置 auth 应用），不是 core_user。
--
--  每条查询包含三部分：
--    【业务问题】这个查询回答什么运营/业务上的问题
--    【考察点】  用到了哪些 SQL 语法（面试常问的）
--    【结果解读】数字出来后应该怎么看
--
--  执行方式：python manage.py dbshell  （或在 analysis/run_analysis.py 中调用）
-- ============================================================================


-- ============================================================================
-- Q1  各分类的商品供给情况
-- ----------------------------------------------------------------------------
-- 【业务问题】平台哪类二手商品最多？哪类供给不足？
-- 【考察点】  LEFT JOIN（保留没有商品的分类）+ GROUP BY + 聚合函数 + ROUND
-- 【结果解读】商品数最多的分类是平台的主要供给；若某分类商品数为 0，
--             说明该类目冷门或未被开发，可考虑引导用户发布。
-- ============================================================================
SELECT
    c.name                          AS 分类名称,
    COUNT(g.id)                     AS 商品数量,
    ROUND(AVG(g.price), 2)          AS 平均价格,
    IFNULL(SUM(g.price), 0)         AS 价格合计
FROM core_category c
LEFT JOIN core_goods g ON g.category_id = c.id
GROUP BY c.id, c.name
ORDER BY 商品数量 DESC, 分类名称;


-- ============================================================================
-- Q2  商品的价格区间分布
-- ----------------------------------------------------------------------------
-- 【业务问题】平台上高价商品和低价商品各占多少？定位是否符合"校园二手"场景？
-- 【考察点】  CASE WHEN 分箱（把连续值切成区间）+ GROUP BY + 占比计算
-- 【结果解读】校园二手场景应以 0–200 元为主；若高价商品占比过高，
--             说明平台定位偏移，或需要针对学生群体的低价商品运营。
-- ============================================================================
SELECT
    CASE
        WHEN price < 50              THEN '0-50 元'
        WHEN price < 200             THEN '50-200 元'
        WHEN price < 1000            THEN '200-1000 元'
        WHEN price < 5000            THEN '1000-5000 元'
        ELSE                              '5000 元以上'
    END                             AS 价格区间,
    COUNT(*)                        AS 商品数量,
    ROUND(COUNT(*) * 100.0 /
          (SELECT COUNT(*) FROM core_goods), 2) AS 占比百分比
FROM core_goods
GROUP BY 价格区间
ORDER BY MIN(price);


-- ============================================================================
-- Q3  订单流转状态分布
-- ----------------------------------------------------------------------------
-- 【业务问题】多少订单完成了交易？多少卡在未支付？多少被取消？
-- 【考察点】  CASE WHEN 做状态映射 + GROUP BY + 占比
-- 【结果解读】这是最核心的运营指标。若"待支付"占比高，说明下单后流失严重，
--             应优化支付流程或增加支付提醒；"已取消"占比高则要排查原因。
-- ============================================================================
SELECT
    CASE order_status
        WHEN 0 THEN '待支付'
        WHEN 1 THEN '已支付'
        WHEN 2 THEN '待发货'
        WHEN 3 THEN '已发货'
        WHEN 4 THEN '已完成'
        WHEN 5 THEN '已取消'
        ELSE        '未知状态'
    END                             AS 订单状态,
    COUNT(*)                        AS 订单数量,
    ROUND(COUNT(*) * 100.0 /
          (SELECT COUNT(*) FROM core_order), 2) AS 占比百分比
FROM core_order
GROUP BY order_status
ORDER BY order_status;


-- ============================================================================
-- Q4  支付状态与售后状态统计
-- ----------------------------------------------------------------------------
-- 【业务问题】实际付款比例是多少？有多少订单进入了售后流程？
-- 【考察点】  多字段分别聚合 + 子查询
-- 【结果解读】pay_status 与 order_status 是两个维度：
--             前者看"钱有没有到"，后者看"流程走到哪"。
--             售后订单占比高可能是商品描述与实物不符的信号。
-- ============================================================================
SELECT
    '支付状态' AS 统计维度,
    CASE pay_status WHEN 0 THEN '未支付' WHEN 1 THEN '已支付'
                    WHEN 2 THEN '已取消' ELSE '未知' END AS 状态,
    COUNT(*) AS 数量
FROM core_order GROUP BY pay_status

UNION ALL

SELECT
    '售后状态' AS 统计维度,
    CASE aftersale_status
        WHEN 0 THEN '无售后' WHEN 1 THEN '售后申请中'
        WHEN 2 THEN '卖家已同意' WHEN 3 THEN '卖家已拒绝'
        WHEN 4 THEN '售后已完成' ELSE '未知' END AS 状态,
    COUNT(*) AS 数量
FROM core_order GROUP BY aftersale_status

ORDER BY 统计维度, 状态;


-- ============================================================================
-- Q5  成交金额与客单价
-- ----------------------------------------------------------------------------
-- 【业务问题】平台实际成交了多少钱？平均每单多少钱？
-- 【考察点】  WHERE 过滤（只算已完成）+ 多聚合函数 + NULL 处理
-- 【结果解读】注意这里只统计 order_status = 4（已完成）的订单，
--             未完成订单不应计入实际营收，这是口径问题，面试常被问。
-- ============================================================================
SELECT
    COUNT(*)                        AS 成交订单数,
    IFNULL(SUM(amount), 0)          AS 成交总额,
    ROUND(IFNULL(AVG(amount), 0), 2) AS 客单价,
    IFNULL(MAX(amount), 0)          AS 最高单笔,
    IFNULL(MIN(amount), 0)          AS 最低单笔
FROM core_order
WHERE order_status = 4;


-- ============================================================================
-- Q6  各分类的成交表现（销量与销售额排行）
-- ----------------------------------------------------------------------------
-- 【业务问题】哪类商品最好卖？哪类只是挂着没人买？
-- 【考察点】  多表 JOIN（订单→商品→分类）+ GROUP BY + 排序 + 聚合
-- 【结果解读】对比"商品数量"（供给）与"成交金额"（需求）：
--             供给多但成交少的分类属于滞销，需要调整推荐策略。
-- ============================================================================
SELECT
    c.name                          AS 分类名称,
    COUNT(DISTINCT g.id)            AS 上架商品数,
    COUNT(o.id)                     AS 成交订单数,
    IFNULL(SUM(o.amount), 0)        AS 成交金额
FROM core_category c
LEFT JOIN core_goods g ON g.category_id = c.id
LEFT JOIN core_order o ON o.goods_id = g.id AND o.order_status = 4
GROUP BY c.id, c.name
ORDER BY 成交金额 DESC, 上架商品数 DESC;


-- ============================================================================
-- Q7  用户的购买行为统计
-- ----------------------------------------------------------------------------
-- 【业务问题】哪些用户在下单？各下了几单、花了多少？
-- 【考察点】  多表 JOIN + GROUP BY + HAVING（分组后过滤）
-- 【结果解读】HAVING 用于过滤聚合后的结果（比如"下单超过 1 单的用户"），
--             这是它和 WHERE 的关键区别，面试高频考点。
--             用户表是 Django 内置的 auth_user，不是 core_user。
-- ============================================================================
SELECT
    u.username                      AS 用户名,
    COUNT(o.id)                     AS 下单数,
    IFNULL(SUM(o.amount), 0)        AS 消费金额,
    IFNULL(ROUND(AVG(o.amount), 2), 0) AS 平均每单
FROM auth_user u
JOIN core_order o ON o.buyer_id = u.id
GROUP BY u.id, u.username
HAVING COUNT(o.id) >= 1
ORDER BY 消费金额 DESC;


-- ============================================================================
-- Q8  商品上架时间分布（供给侧趋势）
-- ----------------------------------------------------------------------------
-- 【业务问题】商品发布集中在哪个月？新用户什么时候活跃？
-- 【考察点】  日期函数 strftime（SQLite）+ GROUP BY + 时间维度聚合
-- 【结果解读】按月看新增商品数，能判断平台活跃度的变化趋势。
--             若使用 MySQL，对应函数为 DATE_FORMAT(create_time, '%Y-%m')。
-- ============================================================================
SELECT
    strftime('%Y-%m', create_time)  AS 月份,
    COUNT(*)                        AS 新增商品数,
    ROUND(AVG(price), 2)            AS 当月均价
FROM core_goods
GROUP BY 月份
ORDER BY 月份;


-- ============================================================================
-- Q9  评价与评分分析
-- ----------------------------------------------------------------------------
-- 【业务问题】平台评价情况如何？平均分多少？有多少评价待审核？
-- 【考察点】  LEFT JOIN + 条件聚合（SUM + CASE WHEN）
-- 【结果解读】平均评分反映交易体验；待审核评价数是运营工作量，
--             需要安排人力及时处理，否则影响其他用户决策。
-- ============================================================================
SELECT
    COUNT(c.id)                                     AS 评价总数,
    IFNULL(ROUND(AVG(c.rating), 2), 0)              AS 平均评分,
    SUM(CASE WHEN c.is_approved = 1 THEN 1 ELSE 0 END) AS 已通过审核,
    SUM(CASE WHEN c.is_approved = 0 THEN 1 ELSE 0 END) AS 待审核,
    SUM(CASE WHEN c.rating >= 4 THEN 1 ELSE 0 END)  AS 好评数,
    SUM(CASE WHEN c.rating <= 2 THEN 1 ELSE 0 END)  AS 差评数
FROM core_comment c;


-- ============================================================================
-- Q10  商品热度排行（收藏数 + 浏览量代理指标）
-- ----------------------------------------------------------------------------
-- 【业务问题】哪些商品最受关注？关注度高但未成交的是哪些？
-- 【考察点】  子查询 / LEFT JOIN 聚合 + 计算列 + 多字段排序
-- 【结果解读】收藏多但没人下单 = 价格偏高或描述有吸引力但转化不好，
--             这是运营的重点优化对象。
-- ============================================================================
SELECT
    g.title                         AS 商品名称,
    c.name                          AS 分类,
    g.price                         AS 价格,
    g.stock                         AS 剩余库存,
    COUNT(DISTINCT f.id)            AS 收藏数,
    COUNT(DISTINCT o.id)            AS 订单数
FROM core_goods g
LEFT JOIN core_category c ON c.id = g.category_id
LEFT JOIN core_favorite f ON f.goods_id = g.id
LEFT JOIN core_order o    ON o.goods_id = g.id AND o.order_status = 4
GROUP BY g.id, g.title, c.name, g.price, g.stock
ORDER BY 收藏数 DESC, 订单数 DESC, 价格 DESC;
