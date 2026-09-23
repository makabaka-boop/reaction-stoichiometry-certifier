# 化学方程式精确配平工作台

中试投料前的全栈配平工作台：React + TypeScript + Vite 编辑化合物矩阵，FastAPI 使用
**纯有理数（`fractions.Fraction`）高斯消元**精确计算零空间，避免浮点消元把近似零
当成约束、或随意选择自由变量把多解体系伪装成唯一配方。

## 判定语义

以反应物为正、产物为负建立元素守恒矩阵 `A`，求右零空间 `A·x = 0`：

| 零空间维数 | 生成向量情况 | 返回状态 |
| --- | --- | --- |
| 0 | — | `NO_BALANCE`（无守恒解） |
| >1 | — | `UNDERDETERMINED`（多解，拒绝给出唯一配方） |
| 1 | 含零项 | `NO_POSITIVE_BALANCE`（`ZERO_COEFFICIENT`） |
| 1 | 翻转整体符号后仍有负分量 | `NO_POSITIVE_BALANCE`（`MIXED_SIGNS`） |
| 1 | 可统一为全正 | `BALANCED`：按分母最小公倍数化为整数，再除以整体 GCD，得到**唯一原始整数系数**及逐元素两侧总数 |

输入整份校验（任一不满足即 400 拒绝整份文档）：2–12 个唯一 ASCII ID、角色仅
`REACTANT`/`PRODUCT`、元素符号必须是 118 个正式 IUPAC 符号、下标为正整数
（拒绝布尔/浮点/零/负数）、组成非空、未知字段拒绝、元素总数 ≤ 20。

任何输入修改都会使页面上的旧证书立即标记为「已撤销」（单调编辑纪元 + 输入指纹），
必须重新求解。

## 运行（Docker Compose）

```bash
docker compose up --build
# web 页面服务: http://localhost:8080   （服务名 web）
# api 接口服务: http://localhost:8000   （服务名 api）
```

## 本地开发

```bash
# 后端
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000

# 前端（Vite 把 /api 代理到 localhost:8000）
cd web
npm install
npm run dev
```

## 测试

```bash
# 后端：含小矩阵整数穷举交叉核对（独立暴力枚举正整数核，与消元实现零共享代码）
cd backend && python3 -m pytest

# 端到端：唯一一条 Playwright 流程——一次录入 → 精确求解 →
# 人工复核 → 非最简/不守恒逐项标红 → 修改输入立即撤销证书
cd web && npx playwright install chromium && npx playwright test
```

## 目录

```
backend/app/
  balancing.py    # Fraction RREF、零空间、LCM/GCD 原始化、人工复核
  validation.py   # 整份文档权威校验
  elements.py     # IUPAC 元素白名单
  certificate.py  # 输入指纹与证书
  main.py         # /api/balance、/api/verify、/api/health
  tests/          # pytest（穷举 + 已知反应 + API 拒绝用例）
web/src/          # React/TS：矩阵编辑、结果与证书、人工系数复核
web/e2e/          # 单条 Playwright 认证流程
docker-compose.yml
```
