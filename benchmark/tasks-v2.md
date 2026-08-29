# 结构化通信试点 · 真实任务集 v2（3 个 dev 任务，均有上游材料）

> 与 v1 的区别：不用"弃权陷阱"，而是用有真实上游材料的任务，测"上游信息有没有被传全"。

---

## 任务 1：带 PRD 的小功能实现

**任务类型**：功能实现
**上游材料**：一份完整 PRD（需求描述 + 5 条验收标准 + 3 条技术约束）

### 上游材料（PRD）

```
## PRD：用户管理页面 CSV 导出

### 需求描述
在现有用户管理页面（src/pages/UserManagement/index.tsx）的工具栏增加一个"导出 CSV"按钮，点击后将当前筛选条件下的用户列表导出为 CSV 文件下载。

### 验收标准
1. 导出的 CSV 包含列：ID、用户名、邮箱、注册时间、状态
2. 导出范围受当前页面筛选条件（状态筛选、搜索关键词）约束
3. 导出文件名格式：users_{YYYYMMDD_HHmmss}.csv
4. 导出过程中按钮显示 loading 状态，防止重复点击
5. 单次导出上限 10000 条，超过时提示用户缩小筛选范围

### 技术约束
- 使用项目已有的 csv 库（papaparse，已在 package.json 中）
- 导出逻辑放在 src/pages/UserManagement/exportCsv.ts，不要写在组件里
- 不引入新的依赖
```

### 你的任务
作为 Dev，基于以上 PRD，给出实现方案（关键设计 + 核心代码片段即可，不需要完整可运行代码）。

### 人工判分关注点
- 验收标准 1-5 有没有都在方案里体现
- 技术约束（papaparse / exportCsv.ts / 不引新依赖）有没有遵守
- 有没有编造 PRD 里没有的需求

---

## 任务 2：带真实报错日志的 bug 修复

**任务类型**：bug 修复
**上游材料**：一段完整的 Python Traceback + 上下文（最近变更、期望行为）

### 上游材料（报错日志 + 上下文）

```
## 报错日志
Traceback (most recent call last):
  File "/app/scripts/import_data.py", line 47, in <module>
    main()
  File "/app/scripts/import_data.py", line 32, in main
    df = pd.read_csv(input_file, encoding='utf-8')
  File "/usr/local/lib/python3.11/site-packages/pandas/io/parsers/readers.py", line 912, in read_csv
    return _read(filepath_or_buffer, kwds)
  ...
  File "/usr/local/lib/python3.11/encodings/utf_8.py", line 16, in decode
    return codecs.utf_8_decode(input, errors, True)
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0 in position 1234: invalid start byte

## 上下文
- 脚本：scripts/import_data.py，用于从 CSV 导入用户数据到数据库
- 输入文件：由运营同事从 Excel 导出的 CSV，可能包含中文
- 最近变更：上周把 pandas 从 1.5 升到 2.1，之后开始报错
- 期望：脚本能正常导入包含中文的 CSV 文件
```

### 你的任务
作为 Dev，基于以上报错日志和上下文，给出根因分析和修复方案（关键代码片段即可）。

### 人工判分关注点
- 有没有从日志里提取到关键信息：UnicodeDecodeError、0xb0 字节、position 1234、pandas read_csv encoding='utf-8'
- 有没有注意到"pandas 从 1.5 升到 2.1"这个上下文线索
- 根因分析是否正确（Excel 导出的 CSV 可能是 GBK/GB2312 编码，不是 UTF-8）
- 修复方案是否合理（encoding='gbk' 或 errors='replace' 或 chardet 检测）
- 有没有编造日志里没有的信息

---

## 任务 3：流水线里有上游产出需要摘要传递

**任务类型**：基于上游产出的技术方案设计
**上游材料**：Product 角色的需求文档摘要（背景 + 核心需求 + 技术约束 + 验收标准）

### 上游材料（Product 产出摘要）

```
## 需求名称：订单超时自动取消

### 背景
用户下单后 30 分钟未支付，订单应自动取消并释放库存。当前系统没有这个机制，导致库存被长期占用。

### 核心需求
1. 订单创建后启动 30 分钟倒计时
2. 倒计时结束时检查订单状态：若仍为"待支付"，则自动取消
3. 取消时释放库存、发送站内信通知用户
4. 若用户在倒计时内完成支付，取消倒计时

### 技术约束（Product 标注）
- 不能用 cron 轮询（延迟不可控）
- 建议用延迟队列（如 Redis ZSET 或 RabbitMQ TTL）
- 取消操作必须幂等（重复触发不能重复扣库存）

### 验收标准
1. 下单后 30 分钟未支付 → 订单状态变为"已取消"
2. 下单后 10 分钟支付 → 订单正常，不取消
3. 取消后库存恢复、用户收到通知
4. 重复触发取消 → 只执行一次
```

### 你的任务
作为 Dev，基于以上 Product 产出，给出技术实现方案（关键设计 + 伪代码即可，不需要完整可运行代码）。

### 人工判分关注点
- 核心需求 1-4 有没有都在方案里体现
- 技术约束有没有遵守（不用 cron、用延迟队列、幂等）
- 验收标准 1-4 有没有对应的验证思路
- 有没有把 Product 的关键信息传递到方案里（30 分钟、释放库存、站内信、幂等）
- 有没有编造 Product 没提的需求
