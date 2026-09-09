---
name: code-annotation-rules-skill
description: 优化代码文件中的注释。当用户要求"优化/完善/精简/补充代码注释"、"按规范整理注释"、"给这段代码加注释"或"清理注释掉的代码"时使用。适用于单文件或批量文件，覆盖 Java、TypeScript/JavaScript、Python、C#、Vue/React 组件等。产出：注释优化后的代码。
---

# 代码注释优化 Skill 约束规范

> 规范来源融合：阿里巴巴 Java 开发手册（注释规约）、Google Java/JavaScript Style Guide、Microsoft C# XML Doc、TSDoc、React/Vue 组件最佳实践。

## 一、总则（优先级最高，先于一切细则执行）

- 【强制】注释与代码同步：改动代码逻辑必须同步更新受影响注释；发现过期注释立即修正或删除。
- 【强制】不残留过程产物：删除被注释掉的代码块、临时调试输出、冗余的中间记录、堆叠的修改历史；确需保留的 `TODO`/`FIXME` 注明责任人与日期，可选择性保留。
- 【强制】注释回答"是什么 / 为什么"，不复述"怎么做"：禁止逐行翻译代码（如 `i++ // i 自增`）。
- 【强制】公共 API（类、方法、组件、props）必须有注释；私有逻辑按"是否有助于他人理解"决定。
- 【推荐】优先中文注释，把问题说清楚，胜过半吊子英文。
- 【强制】精简准确：解释到位的前提下，注释尽可能短；一个注释只讲一件事。

## 二、文件头注释

- 位置：文件最顶部、第一个代码符号之前。
- 必须包含：
  - **文件作用**：这个文件是干什么的
  - **使用场景**：什么时候用、被谁引用、依赖什么
  - **作者**：默认 `@author Lensgcx (GaoCangxiong)`（可覆盖）
  - **创建日期**（可选，格式 `yyyy-MM-dd`）

```java
/**
 * @file UserService.java
 * @description 用户领域服务：封装注册、登录、资料查询等业务逻辑，供 Controller 层调用。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-09
 */
```

```python
"""
@file: user_service.py
@description: 用户领域服务：封装注册、登录、资料查询等业务逻辑，供 Controller 层调用。
@author: Lensgcx (GaoCangxiong)
@date: 2026-09-09
"""
```

【可选】补充 `@version`（版本号）、`@link`（关联文档/模块）。

## 三、类 / 接口 / 模块注释

【强制】所有类必须有注释，说明**职责 + 使用场景**；并添加创建者信息。

```java
/**
 * 用户注册服务。
 * 处理注册校验、密码加密与用户落库，注册流程入口见 RegisterController。
 *
 * @author Lensgcx (GaoCangxiong)
 */
public class UserRegisterService { ... }
```

## 四、方法 / 函数注释

【强制】每个方法必须有注释，除参数、返回值、异常外，还必须说明**该方法做什么**（抽象方法/接口方法尤其如此）。
必须覆盖：
- **做什么**：方法职责、行为
- **输入参数**：每个参数的含义 + 类型 + 边界/约束（能否为 null、取值范围）
- **输出**：返回什么、特殊返回值（如 `null`、`-1`）的含义
- **异常**：何时抛出（如存在）
- **副作用**：是否修改全局状态或入参（建议标注）

```java
/**
 * 按邮箱创建新用户。
 *
 * @param email    用户邮箱，须通过邮箱格式校验，非空
 * @param password 明文密码，长度 8~32 位，须含大小写字母和数字
 * @return 创建成功的用户 ID；邮箱已注册时返回 null
 * @throws IllegalArgumentException 邮箱格式非法或密码不满足强度要求
 */
public Long createUser(String email, String password) { ... }
```

```ts
/**
 * 分页查询订单列表。
 * @param page   页码，从 1 开始
 * @param size   每页条数，默认 20，最大 100
 * @param status 订单状态过滤，传 undefined 表示不过滤
 * @returns 订单列表（不含总数）；无数据时返回空数组
 */
export function queryOrders(page: number, size: number, status?: OrderStatus): Order[] { ... }
```

## 五、变量 / 字段注释

【强制】每个变量/字段用一句话简述**是什么、为什么存在**；不赘述类型（类型已由声明表达）。
- 常量：说明业务含义
- 枚举字段：必须逐一注释
- 魔法数字：必须注释含义

```java
/** 单页最大条数，超过按 100 处理 */
private static final int MAX_PAGE_SIZE = 100;

/** 登录会话缓存：userId -> 会话信息，用于免密校验 */
private Map<Long, UserSession> sessionCache = new HashMap<>();

/** 订单状态：0-待支付 1-已支付 2-已取消 */
private int status;
```

## 六、组件注释（React / Vue 等）

- 组件头：功能 + 使用场景。
- 每个 Props：**含义 + 默认值 + 是否必填**（TS 用可选 `?` 表示非必填，用 `@default` 或解构默认值标注）。

```tsx
/**
 * 商品卡片组件。展示商品主图、价格与加购按钮，用于商品列表与搜索结果页。
 */
export interface ProductCardProps {
  /** 商品 ID，唯一标识，必填 */
  id: string;
  /** 商品名称，展示在卡片标题位置，必填 */
  name: string;
  /** 商品价格（元），保留两位小数，必填 */
  price: number;
  /** 是否显示"已售罄"角标，默认 false */
  soldOut?: boolean;
  /** 图片懒加载开关，默认 true */
  lazyLoad?: boolean;
  /** 点击卡片回调，接收商品 ID，默认不处理 */
  onClick?: (id: string) => void;
}

export function ProductCard({ id, name, price, soldOut = false, lazyLoad = true, onClick }: ProductCardProps) { ... }
```

```ts
// Vue Options API
props: {
  /** 商品名称，必填 */
  name: { type: String, required: true },
  /** 是否售罄，默认 false */
  soldOut: { type: Boolean, default: false },
}
```

## 七、注释形式规范

| 语言/场景 | 文档注释 | 行注释 |
|---|---|---|
| Java | `/** ... */`（Javadoc） | `//`（语句上方另起一行） |
| TypeScript / JavaScript | `/** ... */`（JSDoc / TSDoc） | `//` |
| Python | `""" ... """`（docstring） | `#` |
| C# | `///`（XML Doc） | `//` |
| Vue SFC | 组件内同 TS/JS | `//` |

- 行注释置于被注释语句**上方**或**同行末尾**（短注释），不放在语句下方；行内注释与代码间留一个空格。
- 方法内部复杂逻辑如需多行说明，用块注释 `/* ... */`。

## 八、精简原则与反模式

✅ **值得写注释的**：
- 为什么这样实现（设计取舍、性能考量）
- 边界条件与隐含约束（参数为 null 时怎么办、越界如何处理）
- 业务含义（状态码、魔法数字）
- 易踩坑的调用约定

❌ **反模式（必须避免）**：
- 复述代码：`count++ // 计数加一`
- 空话注释：注释只是方法名的重复
- 注释掉的代码：一律删除；确需保留须说明原因并标注日期
- 过长的变更记录堆叠（过程产物）：合并成一句或直接删除
- 过期注释：与代码不符时必须修正

## 九、执行流程

1. 读取目标文件，识别语言与代码结构（文件头、类/组件、方法/函数、变量/字段、props）。
2. 按本规范逐项检查并重写注释，删除过程产物与反模式注释。
3. 保持原有代码逻辑、命名、格式不变，只动注释。
4. 输出注释优化后的完整文件内容。

## 十、交付检查清单

- [ ] 文件头：作用、使用场景、作者（默认 `Lensgcx (GaoCangxiong)`）齐备
- [ ] 无被注释掉的代码、无调试残留、无冗余过程记录
- [ ] 每个方法：做什么 + 每个参数含义 + 返回值说明
- [ ] 每个变量/字段：一句话说明是什么
- [ ] 组件每个 props：含义 + 默认值
- [ ] 注释与代码一致，无过期注释
- [ ] 每处注释精简，无复述、无空话
- [ ] 注释形式符合对应语言规范（Javadoc / JSDoc / docstring / XML Doc）
