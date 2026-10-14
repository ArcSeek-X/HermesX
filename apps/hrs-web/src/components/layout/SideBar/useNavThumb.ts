/**
 * @file useNavThumb.ts
 * @description 侧边栏「滑行高亮玻璃块」动效子系统（单一模块，参考 SIDEBAR_NAV_THUMB.md）。
 *   把玻璃块定位计算、滑行动画方法与全部触发/同步副作用封装成一个自定义 hook，
 *   让 SidebarNav 只保留 DOM 接线（<div class=navThumb> + 三个 ref 的挂载）。
 *
 *   分层（对齐参考 §2 / §5）：
 *   - 落点解析：matchPath（路由匹配原语，MenuNode/SidebarNav 亦复用）+ resolveHighlightMenuId
 *     —— 解析「当前高亮行」（折叠上移 / 展开回落）；
 *   - 动效底座：slideThumb —— 用 Web Animations API 驱动 transform，零依赖，等价参考的 gsap.to(thumb,{y,...})；
 *   - 触发骨架：useNavThumb —— syncThumb + 路由 watch + 滚动贴合 + ResizeObserver。
 *
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-14
 */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, type RefObject } from 'react';
import type { MenuCollapsedState } from '../../../stores';
import type { NavMenuNode } from '../../../types/moduleMenu';

/**
 * 滑行时长（ms）：
 * - 常规 520ms，对齐参考 DUR.slide=0.52 + power4.out glide（「快出慢收有余韵」）；
 * - 减弱动效 300ms，明显短于常规但仍可被感知（按需求保留可观察的短滑行）；
 * - 跨父级路由切换后的「落点补贴合」180ms：子菜单 height 动画结束后把玻璃从瞬态位置快速收敛到终态。
 */
const THUMB_SLIDE_MS = 520;
const THUMB_SLIDE_REDUCED_MS = 300;
const THUMB_SETTLE_MS = 180;

/** useNavThumb 入参：落点解析与定位/触发所需的输入 */
export interface UseNavThumbOptions {
  /** 菜单数据（主 + 底部合并）：用于解析落点 + 作为列表重建时重新登记 ResizeObserver 的依赖，需为稳定引用 */
  menuItems: NavMenuNode[];
  /** 当前路由路径：解析命中节点 + 区分「用户切换路由」（播滑行）与其它环境变化（瞬时贴合） */
  pathname: string;
  /** 展开判定（与渲染侧同一份）：决定命中项被折叠祖先隐藏时落点是否上移，保证落点与实际可见性一致 */
  isExpanded: (node: NavMenuNode) => boolean;
  /** 侧栏折叠态：仅 offcanvas 态玻璃可见并承载选中背景，其余态隐藏 */
  collapsedState: MenuCollapsedState;
}

/** useNavThumb 返回：供调用方挂到 DOM 的 ref + 解析出的落点 id（供 MenuNode 标记 data-active） */
export interface NavThumbRefs {
  /** 菜单区定位父级（含主菜单 nav + footer），玻璃绝对定位于此 */
  menuAreaRef: RefObject<HTMLDivElement | null>;
  /** 唯一滑行玻璃块（.navThumb） */
  thumbRef: RefObject<HTMLDivElement | null>;
  /** 主菜单滚动容器（ScrollShadow 透传），监听 scroll 让玻璃贴合当前项 */
  navScrollRef: RefObject<HTMLElement | null>;
  /** 当前高亮行（滑行玻璃落点）的菜单 id；无命中为 null（玻璃隐藏）。与路由高亮同源，供兄弟让位复用 */
  highlightMenuId: string | null;
}

/**
 * 读取元素当前的视觉 translateY（px）。动画进行中读取的是该帧动画值，用作下一段滑行的起点，
 * 使取消上一段动画重开时无跳变。无 WAAPI / 无 transform 时返回 0。
 *
 * @param thumb 玻璃块元素
 * @returns 当前 translateY 像素值
 */
const getCurrentY = (thumb: HTMLElement): number => {
  if (typeof window === 'undefined') return 0;
  const m = window.getComputedStyle(thumb).transform;
  if (!m || m === 'none') return 0;
  if (typeof DOMMatrixReadOnly === 'undefined') return 0;
  try {
    return new DOMMatrixReadOnly(m).m42;
  } catch {
    return 0;
  }
};

/**
 * 滑行玻璃定位与动画（可复用单元，参考 §5 的 slideThumb）。
 * 用几何差值把玻璃「贴」到目标行：y = 目标.top - 容器.top（实时 getBoundingClientRect，滚动天然安全）；
 * 动画态用 Web Animations API 从「当前视觉位置」滑到目标，瞬时态直接写 transform。
 * CSS 不写 transition——transform 完全由这里接管，避免两套动画打架（参考 §3.5）。
 *
 * @param thumb        玻璃块元素
 * @param targetRow    目标行（带 data-menu-id 的菜单项）
 * @param menuArea     菜单区定位父级
 * @param animateSlide 是否播滑行；false 为瞬时贴合
 * @param duration     动画时长 ms（由调用方按「减弱动效」策略决定）；instant 时忽略
 * @returns 目标行相对容器的 y（px），供调用方记录「本次落点」以判断后续是否发生偏移
 */
export const slideThumb = (
  thumb: HTMLElement,
  targetRow: HTMLElement,
  menuArea: HTMLElement,
  animateSlide: boolean,
  duration: number,
): number => {
  const ar = menuArea.getBoundingClientRect();
  const tr = targetRow.getBoundingClientRect();
  const y = tr.top - ar.top;
  thumb.style.opacity = '1';
  // 覆盖进行中的动画（对应 gsap overwrite:true），避免多次切换叠加错位；环境无 WAAPI 时跳过
  thumb.getAnimations?.().forEach((a) => a.cancel());
  const canAnimate = typeof thumb.animate === 'function';
  if (!animateSlide || !canAnimate) {
    thumb.style.transform = `translateY(${y}px)`;
    return y;
  }
  // 先取当前视觉位置作起点，再提交终态为内联样式（动画被取消时回落到此、无闪烁），最后用 WAAPI 滑到终态
  const fromY = getCurrentY(thumb);
  thumb.style.transform = `translateY(${y}px)`;
  thumb.animate(
    [{ transform: `translateY(${fromY}px)` }, { transform: `translateY(${y}px)` }],
    { duration, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' },
  );
  return y;
};

// —— 落点解析（自 menuPath.ts 下沉至此，与玻璃定位同源）——

/**
 * 判断菜单配置的路由是否命中当前路径（原 menuPath.ts 的唯一导出，随落点解析一并下沉到此）。
 * MenuNode 判定单节点「自身/子项命中」高亮、SidebarNav 判「父级自动展开」、以及下方 findBestChain 共用。
 *
 * @param routePath 菜单配置的路由；为空表示该项不可跳转，直接判为未命中
 * @param exact     true 要求与当前路径完全相等；false 时当前路径为其子路径也算命中
 * @param pathname  当前浏览器路径
 * @returns 命中返回 true，否则 false
 */
export const matchPath = (
  routePath: string | undefined,
  exact: boolean | undefined,
  pathname: string,
): boolean => {
  if (!routePath) return false;
  return exact ? pathname === routePath : pathname === routePath || pathname.startsWith(`${routePath}/`);
};

/**
 * 两条命中链的优先级比较：路径完全相等 > 前缀命中（容器常以路径前缀注册，不应抢占真正的页面）；同级取更深者。
 * 与既有 reduce 裁决语义一致，供单遍遍历复用。
 */
const isBetterChain = (chainA: NavMenuNode[], chainB: NavMenuNode[], pathname: string): boolean => {
  const aExact = chainA[chainA.length - 1].routePath === pathname ? 1 : 0;
  const bExact = chainB[chainB.length - 1].routePath === pathname ? 1 : 0;
  if (aExact !== bExact) return aExact > bExact;
  return chainA.length > chainB.length;
};

/**
 * 单遍遍历返回「当前路径最佳命中链」（根 → 节点）；无命中返回 null。
 * 相比「先收集全部命中链再 reduce」，边遍历边取最优，省去中间数组。
 */
const findBestChain = (
  menuNodes: NavMenuNode[],
  ancestorChain: NavMenuNode[],
  pathname: string,
): NavMenuNode[] | null => {
  let best: NavMenuNode[] | null = null;
  for (const menuNode of menuNodes) {
    const chain = [...ancestorChain, menuNode];
    // 候选：自身命中，以及子树中的最优（更深优先）
    if (matchPath(menuNode.routePath, menuNode.exact, pathname) && (!best || isBetterChain(chain, best, pathname))) {
      best = chain;
    }
    if (menuNode.children?.length) {
      const childBest = findBestChain(menuNode.children, chain, pathname);
      if (childBest && (!best || isBetterChain(childBest, best, pathname))) best = childBest;
    }
  }
  return best;
};

/**
 * 解析滑行玻璃落点菜单 id —— 即「当前高亮行」，与路由高亮同源的单一真源（自 menuPath.ts 下沉至此）。
 *
 * 规则：
 * 1. 落点跟随当前路由命中的菜单；多节点同时命中时先取「路径完全相等」者、再取更深者，结果与数组顺序无关；
 * 2. 命中项若被某个折叠的祖先隐藏（子菜单未渲染，DOM 中不存在），落点上移到链上第一个折叠的祖先
 *    （它必然可见），对应「折叠含激活子项的一级菜单时玻璃落到该一级菜单上」；
 * 3. 祖先全部展开时落点即命中节点自身，对应「重新展开后玻璃回到激活子项」；
 * 4. 无任何菜单命中当前路由时返回 null（玻璃隐藏）。
 *
 * @param menuNodes  菜单节点列表（主菜单 + 底部菜单合并后的全量）
 * @param pathname   当前浏览器路径
 * @param isExpanded 展开判定（与渲染侧同一份，保证落点与实际可见性一致）
 * @returns 落点菜单 id；无命中返回 null
 */
export const resolveHighlightMenuId = (
  menuNodes: NavMenuNode[],
  pathname: string,
  isExpanded: (node: NavMenuNode) => boolean,
): string | null => {
  const best = findBestChain(menuNodes, [], pathname);
  if (!best) return null;
  // 链上第一个「自身折叠」的节点即落点（链上最后一个可见节点）；末节点自身折叠时仍可见，玻璃落在它身上
  const collapsedIndex = best.findIndex((node, index) => index < best.length - 1 && !isExpanded(node));
  const target = collapsedIndex >= 0 ? best[collapsedIndex] : best[best.length - 1];
  return target.menuId;
};

/**
 * 侧边栏滑行玻璃子系统 hook：接管 refs、落点解析、定位计算与全部同步副作用。
 *
 * 触发策略（对齐参考 §3.4「克制原则」）：
 * - 仅「用户切换路由」播滑行；
 * - 首次挂载 / 折叠展开 / 菜单数据变化 / resize / 滚动一律瞬时贴合（避免无意义位移）；
 * - 跨父级路由切换时目标父级子菜单 height 动画未结束会令落点 Y 短暂偏移，滑行后再补一段短滑行贴合修正。
 *
 * 减弱动效（prefers-reduced-motion）：参考是尊重系统完全静止；此处按需求保留可观察的短滑行，
 * 时长取 THUMB_SLIDE_REDUCED_MS(0.30s)，明显短于常规 THUMB_SLIDE_MS(0.52s)。
 *
 * @param options 见 UseNavThumbOptions
 * @returns refs + highlightMenuId，供调用方挂 DOM 与标记高亮行
 */
export const useNavThumb = ({
  menuItems,
  pathname,
  isExpanded,
  collapsedState,
}: UseNavThumbOptions): NavThumbRefs => {
  const menuAreaRef = useRef<HTMLDivElement | null>(null);
  const thumbRef = useRef<HTMLDivElement | null>(null);
  const navScrollRef = useRef<HTMLElement | null>(null);
  const reduceMotionRef = useRef(
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );

  // 落点解析（当前高亮行）：命中路由的菜单；被折叠祖先隐藏时上移到最近可见的祖先行。供玻璃定位与 MenuNode 复用
  const highlightMenuId = useMemo(
    () => resolveHighlightMenuId(menuItems, pathname, isExpanded),
    [menuItems, pathname, isExpanded],
  );

  /** 按落点 menuId 精确定位目标行（而非取首个 [data-active]）：折叠动画中「正在退场」的旧行仍在 DOM，按首个匹配会贴错 */
  const findTarget = useCallback((): HTMLElement | null => {
    const area = menuAreaRef.current;
    if (!area) return null;
    if (collapsedState !== 'offcanvas') return null;
    const rows = Array.from(area.querySelectorAll<HTMLElement>('[data-menu-id]'));
    return rows.find((row) => row.dataset.menuId === highlightMenuId) ?? null;
  }, [collapsedState, highlightMenuId]);

  // 记录最近一次定位的落点 y，供跨父级切换后的「漂移检测」比对
  const lastTargetYRef = useRef<number | null>(null);
  const syncThumb = useCallback(
    (animateSlide: boolean, durationOverride?: number) => {
      const area = menuAreaRef.current;
      const thumb = thumbRef.current;
      if (!area || !thumb) return;
      const target = findTarget();
      if (!target) {
        thumb.style.opacity = '0';
        return;
      }
      const dur = durationOverride ?? (reduceMotionRef.current ? THUMB_SLIDE_REDUCED_MS : THUMB_SLIDE_MS);
      lastTargetYRef.current = slideThumb(thumb, target, area, animateSlide, dur);
    },
    [findTarget],
  );

  // syncThumbRef：把最新 syncThumb 写入 ref 供滚动 / ResizeObserver 副作用调用，避免把它们写进依赖。
  // 关键：syncThumb 身份随高亮变化而变化，若 RO 依赖它就会在每次路由切换时重新 observe，
  // 而新建的 ResizeObserver 会立刻触发一次初始回调 → syncThumb(false) 把滑动动画取消成瞬贴，
  // 这正是「切换无动画、时长设多大都瞬间变化」的根因。
  const syncThumbRef = useRef(syncThumb);
  useLayoutEffect(() => {
    syncThumbRef.current = syncThumb;
  });

  // 重新测量当前落点的 y（相对容器）；用于跨父级切换后的漂移检测
  const measureTargetY = useCallback((): number | null => {
    const area = menuAreaRef.current;
    const target = findTarget();
    if (!area || !target) return null;
    return target.getBoundingClientRect().top - area.getBoundingClientRect().top;
  }, [findTarget]);

  // 触发：仅「用户切换路由」播滑行，其余瞬时对齐。
  // 跨父级切换时目标父级子菜单 height 动画未结束会令落点 Y 短暂偏移；滑行后做一次「漂移检测」：
  // 仅当落点真的移动了（> 2px）才补一段短滑行修正，否则让主动画播完（否则会被无条件掐断、时长失效）。
  const prevPathRef = useRef<string | null>(null);
  useLayoutEffect(() => {
    const routeChanged = prevPathRef.current !== null && prevPathRef.current !== pathname;
    prevPathRef.current = pathname;
    syncThumb(routeChanged);
    if (!routeChanged) return;
    const id = window.setTimeout(() => {
      const yNow = measureTargetY();
      if (yNow !== null && lastTargetYRef.current !== null && Math.abs(yNow - lastTargetYRef.current) > 2) {
        syncThumbRef.current(true, THUMB_SETTLE_MS);
      }
    }, 300);
    return () => window.clearTimeout(id);
  }, [pathname, menuItems, collapsedState, syncThumb, measureTargetY]);

  // 主菜单滚动时让玻璃贴合当前项（rAF 节流，瞬时态避免滑行拖影）。仅挂载时绑定一次，逻辑走最新引用。
  useEffect(() => {
    const nav = navScrollRef.current;
    if (!nav) return;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        syncThumbRef.current(false);
      });
    };
    nav.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      nav.removeEventListener('scroll', onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  // 尺寸变化→瞬时对齐。必须观测两处，缺一即错位：
  // 1) menuArea（菜单区容器）：侧栏宽度动画 / 折叠态切换导致容器尺寸变化；
  // 2) 菜单列表 ul：一级菜单开合时子菜单做 height 0↔auto 动画，逐帧改变的是列表自身高度，
  //    而 menuArea 定高（nav flex-1 内部滚动）尺寸恒定，容器级观测收不到这类变化——缺它则开合后玻璃停在旧坐标。
  // 依赖仅 [menuItems]（菜单结构变化才重新登记观测），逻辑走 syncThumbRef；
  // 不能依赖 syncThumb——否则每次路由切换都重新 observe，其初始回调会把滑动动画瞬贴打断（见 syncThumbRef 注释）。
  useEffect(() => {
    const area = menuAreaRef.current;
    if (!area) return;
    const ro = new ResizeObserver(() => syncThumbRef.current(false));
    ro.observe(area);
    area.querySelectorAll('ul').forEach((list) => ro.observe(list));
    return () => ro.disconnect();
  }, [menuItems]);

  return { menuAreaRef, thumbRef, navScrollRef, highlightMenuId };
};

export default useNavThumb;
