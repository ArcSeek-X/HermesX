/**
 * 类名合并工具
 *
 * 作用：封装 clsx 与 tailwind-merge，用于在 React 组件中条件性地组合 CSS 类名，
 * 并自动合并/去重存在冲突的 Tailwind 原子类（例如同时传入 "px-2" 与 "px-4" 时只保留后者）。
 * 这是前端 UI 层统一使用的类名拼接入口。
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * 合并类名。
 *
 * @param inputs - 任意类型的类名参数（字符串、数组、对象条件写法等），由 clsx 解析
 * @returns 经过 tailwind-merge 去重后的最终 className 字符串
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
