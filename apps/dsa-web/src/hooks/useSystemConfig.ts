import { useCallback, useMemo, useRef, useState } from 'react';
import { createParsedApiError, getParsedApiError, type ParsedApiError } from '../api/error';
import { systemConfigApi, SystemConfigConflictError, SystemConfigValidationError } from '../api/systemConfig';
import type {
  ConfigValidationIssue,
  SystemConfigCategorySchema,
  SystemConfigItem,
  SystemConfigUpdateItem,
} from '../types/systemConfig';
import { serializeStockListValue } from '../utils/stockList';

/** Toast 提示状态：成功提示、错误提示（携带解析后的错误信息），或空。 */
type ToastState = {
  type: 'success';
  message: string;
} | {
  type: 'error';
  error: ParsedApiError;
} | null;

/** 当前可重试的动作类型：加载失败重试 / 保存失败重试 / 无。 */
type RetryAction = 'load' | 'save' | null;

/** 保存操作的返回结果，供调用方判断成功与否及校验问题。 */
type SaveResult = {
  success: boolean;
  message?: string;
  issues?: ConfigValidationIssue[];
};

/** 各配置分类在前端 Tab 中的展示顺序（数值越小越靠前）。 */
const CATEGORY_DISPLAY_ORDER: Record<string, number> = {
  base: 10,
  ai_model: 20,
  data_source: 30,
  notification: 40,
  system: 50,
  agent: 55,
  backtest: 60,
  uncategorized: 99,
};

/**
 * 按 schema.displayOrder 升序、同序时按 key 字典序排列配置项，保证展示稳定一致。
 * 返回新数组，不修改入参。
 */
function sortItemsByOrder(items: SystemConfigItem[]): SystemConfigItem[] {
  return [...items].sort((a, b) => {
    const left = a.schema?.displayOrder ?? 9999;
    const right = b.schema?.displayOrder ?? 9999;
    if (left !== right) {
      return left - right;
    }
    return a.key.localeCompare(b.key);
  });
}

/** 判断某配置项 schema 是否标记为「多值」（兼容 multiValue / multi_value 两种写法）。 */
function isMultiValueSchema(schema: SystemConfigItem['schema'] | undefined): boolean {
  const validation = (schema?.validation ?? {}) as Record<string, unknown>;
  return Boolean(validation.multiValue ?? validation.multi_value);
}

/**
 * 将字段值规范化为可比较的标准形态：
 * - STOCK_LIST 走专用的股票列表序列化；
 * - 多值字段：按逗号拆分、去空白、去空项后重新拼接，消除顺序/空格差异；
 * - 普通字段：原样返回。
 * 规范化后，可准确判断「草稿值」与「服务端当前值」是否真的发生变化。
 */
function normalizeFieldValue(value: string, schema: SystemConfigItem['schema'] | undefined): string {
  if ((schema?.key ?? '').toUpperCase() === 'STOCK_LIST') {
    return serializeStockListValue(value);
  }

  if (!isMultiValueSchema(schema)) {
    return value;
  }

  return value
    .split(',')
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)
    .join(',');
}

export function useSystemConfig() {
  // ===== Server state：来自服务端、作为「已提交真值」的配置 =====
  // 配置版本号，保存时用于乐观并发控制（防止覆盖他人修改）
  const [configVersion, setConfigVersion] = useState<string>('');
  // 敏感字段的脱敏令牌，随配置下发，保存时必须原样回传
  const [maskToken, setMaskToken] = useState<string>('******');
  // 服务端返回的全部配置项（含当前已提交值）
  const [serverItems, setServerItems] = useState<SystemConfigItem[]>([]);

  // ===== UI state：界面交互态 =====
  // 草稿值：用户在表单中的临时输入，尚未提交
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  // 当前选中的配置分类 Tab
  const [activeCategory, setActiveCategory] = useState<string>('base');
  // 服务端/客户端校验产生的问题列表
  const [validationIssues, setValidationIssues] = useState<ConfigValidationIssue[]>([]);
  // 顶部 Toast 提示
  const [toast, setToast] = useState<ToastState>(null);

  // ===== Request state：异步请求态 =====
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  // 加载/保存失败时的解析化错误（便于统一展示）
  const [loadError, setLoadError] = useState<ParsedApiError | null>(null);
  const [saveError, setSaveError] = useState<ParsedApiError | null>(null);
  // 记录最近一次失败动作类型，供错误界面「重试」按钮复用
  const [retryAction, setRetryAction] = useState<RetryAction>(null);
  // 最新的 serverItems 按 key 索引映射（ref 形式，供回调中无依赖读取）
  const serverItemByKeyRef = useRef<Record<string, SystemConfigItem>>({});

  // 合并「草稿值覆盖服务端值」后的配置项列表，并按展示顺序排序。
  // 表单展示以 draftValues 优先，未编辑的项回落到服务端值。
  const mergedItems = useMemo(() => {
    return sortItemsByOrder(
      serverItems.map((item) => ({
        ...item,
        value: draftValues[item.key] ?? item.value,
      })),
    );
  }, [draftValues, serverItems]);

  // 按 key 建立服务端配置项索引；同步写入 ref 供无依赖回调读取。
  const serverItemByKey = useMemo(() => {
    const map: Record<string, SystemConfigItem> = {};
    for (const item of serverItems) {
      map[item.key] = item;
    }
    serverItemByKeyRef.current = map;
    return map;
  }, [serverItems]);

  // 由配置项的 schema.category 推断前端分类 Tab（标题做首字母大写处理），并按序排列。
  const categories = useMemo<SystemConfigCategorySchema[]>(() => {
    const categoryMap = new Map<string, SystemConfigCategorySchema>();
    for (const item of mergedItems) {
      if (!item.schema) {
        continue;
      }

      const category = item.schema.category;
      if (!categoryMap.has(category)) {
        categoryMap.set(category, {
          category,
          title: category.replace('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
          description: '',
          displayOrder: CATEGORY_DISPLAY_ORDER[category] ?? 999,
          fields: [],
        });
      }
      categoryMap.get(category)?.fields.push(item.schema);
    }

    return [...categoryMap.values()].sort((a, b) => a.displayOrder - b.displayOrder);
  }, [mergedItems]);

  // 按分类分组配置项，便于按 Tab 渲染对应字段。
  const itemsByCategory = useMemo(() => {
    const map: Record<string, SystemConfigItem[]> = {};
    for (const item of mergedItems) {
      const category = item.schema?.category ?? 'uncategorized';
      if (!map[category]) {
        map[category] = [];
      }
      map[category].push(item);
    }
    return map;
  }, [mergedItems]);

  // 计算「脏字段」：草稿值与服务端值经规范化后不一致的项。
  const dirtyKeys = useMemo(() => {
    const keys: string[] = [];
    for (const item of serverItems) {
      const draftRaw = draftValues[item.key];
      if (draftRaw === undefined) {
        continue;
      }

      const normalizedDraft = normalizeFieldValue(draftRaw, item.schema);
      const normalizedCurrent = normalizeFieldValue(item.value, item.schema);
      if (normalizedDraft !== normalizedCurrent) {
        keys.push(item.key);
      }
    }
    return keys;
  }, [draftValues, serverItems]);

  // 是否存在未保存修改，供「保存」按钮可用态等使用
  const hasDirty = dirtyKeys.length > 0;

  // 将校验问题按 key 分组，便于字段级错误展示。
  const issueByKey = useMemo(() => {
    const map: Record<string, ConfigValidationIssue[]> = {};
    for (const issue of validationIssues) {
      if (!map[issue.key]) {
        map[issue.key] = [];
      }
      map[issue.key].push(issue);
    }
    return map;
  }, [validationIssues]);

  /**
   * 将服务端载荷写入 state。
   * @param preserveDirty 为 true 时保留用户已编辑但未提交的草稿（仅刷新服务端真值）
   * @param committedKeys 已提交成功的 key 集合，这些项强制以服务端新值覆盖草稿
   */
  const applyServerPayload = useCallback(
    (
      items: SystemConfigItem[],
      version: string,
      token: string,
      options?: { preserveDirty?: boolean; committedKeys?: string[] },
    ) => {
      const sorted = sortItemsByOrder(items);
      const previousServerMap = serverItemByKeyRef.current;
      const committedKeys = new Set(options?.committedKeys ?? []);
      const preserveDirty = options?.preserveDirty ?? false;

      // 更新服务端真值、版本号与脱敏令牌
      setServerItems(sorted);
      setConfigVersion(version);
      setMaskToken(token || '******');

      // 重新推导草稿：已提交的 key 用新值；preserveDirty 时保留脏草稿；其余回落服务端值
      setDraftValues((prevDraft) => {
        const nextDraft: Record<string, string> = {};
        for (const item of sorted) {
          if (committedKeys.has(item.key)) {
            nextDraft[item.key] = item.value;
            continue;
          }

          if (preserveDirty) {
            const previousServerValue = previousServerMap[item.key]?.value;
            const hasDraft = prevDraft[item.key] !== undefined;
            const wasDirty = hasDraft && prevDraft[item.key] !== previousServerValue;
            nextDraft[item.key] = wasDirty ? prevDraft[item.key] : item.value;
            continue;
          }

          nextDraft[item.key] = item.value;
        }
        return nextDraft;
      });

      // 若当前分类 Tab 已不存在，则回落到第一个分类
      const defaultCategory = sorted[0]?.schema?.category || 'base';
      setActiveCategory((current) => {
        const exists = sorted.some((item) => item.schema?.category === current);
        return exists ? current : defaultCategory;
      });
      setValidationIssues([]);
    },
    [],
  );

  /** 加载配置：拉取服务端配置并写入 state；返回是否成功（供调用方判断）。 */
  const load = useCallback(async (): Promise<boolean> => {
    setIsLoading(true);
    setLoadError(null);
    setRetryAction(null);

    try {
      const config = await systemConfigApi.getConfig(true);
      applyServerPayload(config.items, config.configVersion, config.maskToken);
      setToast(null);
      return true;
    } catch (error: unknown) {
      setLoadError(getParsedApiError(error));
      setRetryAction('load');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [applyServerPayload]);

  /** 放弃所有未保存修改：草稿回退到服务端值，并清除校验问题与保存错误。 */
  const resetDraft = useCallback(() => {
    const next: Record<string, string> = {};
    for (const item of serverItems) {
      next[item.key] = item.value;
    }
    setDraftValues(next);
    setValidationIssues([]);
    setSaveError(null);
  }, [serverItems]);

  /** 部分更新草稿（如联动修改多个相关字段），不触发提交。 */
  const applyPartialUpdate = useCallback((updatedItems: Array<{ key: string; value: string }>) => {
    setDraftValues((prevDraft) => {
      const nextDraft = { ...prevDraft };
      for (const item of updatedItems) {
        nextDraft[item.key] = item.value;
      }
      return nextDraft;
    });
  }, []);

  /**
   * 外部保存成功后刷新：重新拉取配置，但保留用户仍在编辑的脏草稿，
   * 仅以 committedKeys 覆盖已提交项，避免覆盖其它未保存改动。
   */
  const refreshAfterExternalSave = useCallback(
    async (committedKeys: string[]) => {
      const config = await systemConfigApi.getConfig(true);
      applyServerPayload(config.items, config.configVersion, config.maskToken, {
        preserveDirty: true,
        committedKeys,
      });
    },
    [applyServerPayload],
  );

  /** 设置单个字段的草稿值（受控输入 onChange 调用）。 */
  const setDraftValue = useCallback((key: string, value: string) => {
    setDraftValues((previous) => ({
      ...previous,
      [key]: value,
    }));
  }, []);

  /** 计算需要提交的变更项：将脏字段按 schema 规范化后输出（过滤掉规范后无差异的项）。 */
  const getChangedItems = useCallback((): SystemConfigUpdateItem[] => {
    return dirtyKeys
      .map((key) => {
        const serverItem = serverItemByKey[key];
        const normalizedValue = normalizeFieldValue(draftValues[key] ?? '', serverItem?.schema);
        return {
          key,
          value: normalizedValue,
        };
      })
      .filter((item) => {
        const serverItem = serverItemByKey[item.key];
        const normalizedCurrent = normalizeFieldValue(serverItem?.value ?? '', serverItem?.schema);
        return item.value !== normalizedCurrent;
      });
  }, [dirtyKeys, draftValues, serverItemByKey]);

  /**
   * 保存配置：
   * 1. 若未传 changedItems，则自动从草稿中推导变更；无变更则提示并返回成功。
   * 2. 先调用校验接口，校验失败则展示字段级错误并终止。
   * 3. 校验通过后提交更新（携带版本号与脱敏令牌做并发控制），再重新拉取最新配置。
   * 4. 捕获校验错误、版本冲突错误与其它未知错误，分别给出对应提示。
   */
  const save = useCallback(async (changedItems?: SystemConfigUpdateItem[]): Promise<SaveResult> => {
    const explicitItems = changedItems ?? [];
    const resolvedChangedItems = explicitItems.length > 0 ? explicitItems : getChangedItems();

    if (!explicitItems.length && !hasDirty) {
      setToast({ type: 'success', message: '当前没有可保存的修改。' });
      return { success: true, message: '当前没有可保存的修改' };
    }

    if (!resolvedChangedItems.length) {
      setToast({ type: 'success', message: '当前没有可保存的修改。' });
      return { success: true, message: '当前没有可保存的修改' };
    }

    setIsSaving(true);
    setSaveError(null);
    setRetryAction(null);

    try {
      const validateResult = await systemConfigApi.validate({ items: resolvedChangedItems });
      setValidationIssues(validateResult.issues || []);

      if (!validateResult.valid) {
        setSaveError(createParsedApiError({
          title: '配置校验未通过',
          message: '请先修正表单错误后再保存。',
          rawMessage: '配置校验未通过，请先修正表单错误。',
          category: 'http_error',
        }));
        setRetryAction('save');
        return {
          success: false,
          message: '配置校验未通过',
          issues: validateResult.issues,
        };
      }

      const updateResult = await systemConfigApi.update({
        configVersion,
        maskToken,
        reloadNow: true,
        items: resolvedChangedItems,
      });

      const refreshed = await systemConfigApi.getConfig(true);
      applyServerPayload(refreshed.items, refreshed.configVersion, refreshed.maskToken);

      const warningText = updateResult.warnings?.length
        ? `；警告：${updateResult.warnings.join('；')}`
        : '';
      setToast({ type: 'success', message: `配置已更新${warningText}` });
      return { success: true };
    } catch (error: unknown) {
      if (error instanceof SystemConfigValidationError) {
        setValidationIssues(error.issues);
        setSaveError(error.parsedError);
      } else if (error instanceof SystemConfigConflictError) {
        // 版本冲突：提示用户先重新加载，避免基于过期版本覆盖
        setSaveError(createParsedApiError({
          title: '配置版本冲突',
          message: `${error.message}，请先重新加载配置。`,
          rawMessage: error.parsedError.rawMessage,
          status: error.parsedError.status,
          category: error.parsedError.category,
        }));
      } else {
        setSaveError(getParsedApiError(error));
      }

      setToast({ type: 'error', error: getParsedApiError(error) });
      setRetryAction('save');
      return { success: false, message: '保存失败' };
    } finally {
      setIsSaving(false);
    }
  }, [
    applyServerPayload,
    configVersion,
    getChangedItems,
    hasDirty,
    maskToken,
  ]);

  /** 根据上次失败的动作类型，重试「加载」或「保存」。 */
  const retry = useCallback(async () => {
    if (retryAction === 'load') {
      await load();
      return;
    }
    if (retryAction === 'save') {
      await save();
    }
  }, [load, retryAction, save]);

  /** 清除当前 Toast 提示。 */
  const clearToast = useCallback(() => {
    setToast(null);
  }, []);

  return {
    // Server state
    configVersion,
    maskToken,
    serverItems,
    categories,
    itemsByCategory,
    issueByKey,

    // UI state
    activeCategory,
    setActiveCategory,
    hasDirty,
    dirtyCount: dirtyKeys.length,
    toast,
    clearToast,

    // Request state
    isLoading,
    isSaving,
    loadError,
    saveError,
    retryAction,

    // Actions
    load,
    retry,
    save,
    resetDraft,
    setDraftValue,
    getChangedItems,
    applyPartialUpdate,
    refreshAfterExternalSave,
  };
}
