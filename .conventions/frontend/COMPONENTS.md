# 前端组件封装基础Skill

> 组件标准化二次封装技能：全程使用 Tailwind 原生样式或者Tailwind.config定义的样式、不新增自定义 CSS、完整保留 HeroUI 原生能力，仅做业务增量增强。

- **描述**：组件标准化二次封装技能，全程使用 Tailwind 原生样式、不新增自定义 CSS、完整保留 原UI库 的原生能力，仅做业务增量增强。
- **适用范围**：React + TypeScript + TailwindCSS + UI组件库 业务组件封装
- **适配平台**：CodeBuddy / DeepSeek Harness / Cursor / Claude Code
- **封装对象**：HeroUI

---

## 一、强制核心规则（必须严格遵守）

- **禁止修改原生源码**：不修改、不复制、不覆盖 `node_modules` 内 HeroUI 源码，所有定制统一在业务层外层包装实现。
- **禁止自定义样式文件**：所有样式仅使用 Tailwind 原生样式或者Tailwind.config定义的样式，不新建 CSS、SCSS 样式文件。
- **禁止使用强制权重**：严禁使用 `!important` 覆盖样式。
- **完整透传原生属性**：必须完整继承并透传原生组件所有 Props、事件、TS 类型、枚举，不阉割任何原生能力。
- **统一使用官方样式合并工具**：必须使用 HeroUI 内置 `classNames` 合并样式，禁止手动字符串拼接类名。
- **外部样式优先级最高**：外部传入的 `className` 永远放在合并最后，支持全局覆写所有默认样式。
- **仅做增量业务增强**：只新增业务属性、默认样式、业务逻辑，不修改原生组件核心渲染与交互逻辑。

---

## 二、固定组件架构（所有组件统一）

所有的二次封装组件必须遵循以下结构：

1. 通过 `React.ComponentProps<typeof 原生组件>` 完整继承原生 TS 类型
2. 通过 TS 交叉类型扩展业务自定义属性
3. 解构自定义业务属性，剩余参数全部透传给原生组件
4. 使用官方 `classNames` 分层合并 Tailwind 样式

---

## 三、标准固定代码模板

1. 可参考目录文件：apps/hrs-web/src/components/basic/HrsButton.tsx
2. 或参照下面代码模板：

```tsx
import React from 'react';
import { 原生组件 } from '@heroui/xxx';
import { cn } from '../../utils/cn';

// 继承原生所有类型 + 扩展业务类型
export type Biz组件Props = React.ComponentProps<typeof 原生组件> & {
  // 此处按需定义业务自定义属性
  bizType?: '默认' | '成功' | '警告' | '危险';
};

export const Biz组件 = ({
  bizType,
  className,
  ...props
}: Biz组件Props) => {

  // 业务预设 Tailwind 样式
  const bizClass = {
    默认: 'bg-blue-600 text-white hover:bg-blue-700',
    成功: 'bg-emerald-600 text-white hover:bg-emerald-700',
    警告: 'bg-amber-500 text-white hover:bg-amber-600',
    危险: 'bg-red-600 text-white hover:bg-red-700'
  }[bizType || '默认'];

  return (
    <原生组件
      {...props}
      className={cn(bizClass, className)}
    />
  );
};
```

---

## 四、目录与导出规范

1. 组件命名大写，如：HrsButton、Table
2. 组件目录：
基于UI组件的二次封装：基础组件统一目录结构：`src/components/basic/组件名/`
基于基础组件的疯转：公共组件统一目录结构：`src/components/common/组件名/`

3. 组件在 “/components/basic/index.ts” 或 “/components/common/index.ts下”,进行挂载注册。
`index.ts` 固定写法：

```ts
export * from './组件名';
```

> 所有组件使用命名导出，禁止默认导出，对齐 HeroUI 官方风格。

---

## 五、AI 输出规范

每次封装组件必须完整输出：

- 完整 TSX 组件源码
- 完整 TS 类型定义
- `index.ts` 导出文件挂载
- 组件文件的介绍（写在组件的头部）
- 组件的代码注释

