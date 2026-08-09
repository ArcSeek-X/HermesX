/**
 * 股票代码规范化工具
 *
 * 作用：把用户或接口中各种写法的股票代码统一成项目内部的标准形式，剥离交易所前缀/后缀，
 * 并对港股代码补齐为 5 位 canonical 形式（如 hk1810 → HK01810、00700.HK → HK00700）。
 * 该逻辑镜像后端 data_provider.base.normalize_stock_code 的行为，保证前后端一致性。
 *
 * 转换示例：
 *   600519      → 600519     SH600519    → 600519
 *   600519.SH   → 600519     SH.600519   → 600519
 *   SZ000001    → 000001     000001.SZ   → 000001
 *   BJ920748    → 920748     920748.BJ   → 920748
 *   HK00700     → HK00700    00700       → HK00700
 *   00700.HK    → HK00700
 *   hk1810      → HK01810    1810.HK     → HK01810
 *   7203.T      → 7203.T     005930.KS   → 005930.KS
 *   AAPL        → AAPL       TSLA        → TSLA
 */

/**
 * 规范化股票代码：剥离交易所前缀/后缀，并统一港股为 5 位 canonical 形式。
 *
 * @param stockCode - 原始股票代码字符串
 * @returns 规范化后的代码
 */
export function normalizeStockCode(stockCode: string): string {
  const code = stockCode.trim();
  const upper = code.toUpperCase();

  // Normalize HK prefix to a canonical 5-digit form (e.g. hk1810 → HK01810)
  if (upper.startsWith('HK') && !upper.startsWith('HK.')) {
    const candidate = upper.slice(2);
    if (/^\d{1,5}$/.test(candidate) && candidate.length >= 1 && candidate.length <= 5) {
      return `HK${candidate.padStart(5, '0')}`;
    }
  }

  // Pure 5-digit codes are HK stocks by validateStockCode() contract.
  if (/^\d{5}$/.test(upper)) {
    return `HK${upper}`;
  }

  // Strip SH/SZ prefix (e.g. SH600519 → 600519)
  if ((upper.startsWith('SH') || upper.startsWith('SZ')) && !upper.startsWith('SH.') && !upper.startsWith('SZ.')) {
    const candidate = code.slice(2);
    if (/^\d{5,6}$/.test(candidate)) {
      return candidate;
    }
  }

  // Strip dotted SH/SZ prefix (e.g. SH.600519 → 600519)
  if (upper.startsWith('SH.') || upper.startsWith('SZ.')) {
    const candidate = code.slice(3);
    if (/^\d{5,6}$/.test(candidate)) {
      return candidate;
    }
  }

  // Strip BJ prefix (e.g. BJ920748 → 920748)
  if (upper.startsWith('BJ') && !upper.startsWith('BJ.')) {
    const candidate = code.slice(2);
    if (/^\d{6}$/.test(candidate)) {
      return candidate;
    }
  }

  // Strip dotted BJ prefix (e.g. BJ.920748 → 920748)
  if (upper.startsWith('BJ.')) {
    const candidate = code.slice(3);
    if (/^\d{6}$/.test(candidate)) {
      return candidate;
    }
  }

  // Strip .SH/.SZ/.BJ suffix and .HK suffix with HK-prefix canonicalization
  if (code.includes('.')) {
    const dotIndex = code.lastIndexOf('.');
    const base = code.slice(0, dotIndex);
    const suffix = code.slice(dotIndex + 1).toUpperCase();

    // JP/KR Yahoo suffix-only codes are canonical as uppercase suffix forms.
    if (suffix === 'T' && /^\d{4,5}$/.test(base)) {
      return `${base}.${suffix}`;
    }
    if ((suffix === 'KS' || suffix === 'KQ') && /^\d{6}$/.test(base)) {
      return `${base}.${suffix}`;
    }
    // TW Yahoo suffix-only codes (TWSE `.TW` / TPEx `.TWO`), base 4-6 digits.
    if ((suffix === 'TW' || suffix === 'TWO') && /^\d{4,6}$/.test(base)) {
      return `${base}.${suffix}`;
    }

    // 00700.HK → HK00700
    if (suffix === 'HK' && /^\d{1,5}$/.test(base)) {
      return `HK${base.padStart(5, '0')}`;
    }

    // 600519.SH → 600519
    if ((suffix === 'SH' || suffix === 'SS' || suffix === 'SZ' || suffix === 'BJ') && /^\d+$/.test(base)) {
      return base;
    }
  }

  return code;
}

/**
 * 生成用于比较的匹配键：先规范化再转大写，使不同写法的同一只股票能被识别为相等。
 *
 * @param stockCode - 股票代码
 * @returns 大写的规范化代码
 */
function stockCodeMatchKey(stockCode: string): string {
  return normalizeStockCode(stockCode).toUpperCase();
}

/**
 * 判断两个股票代码是否代表同一只股票（忽略前缀/后缀与大小写差异）。
 *
 * @param left - 第一个代码
 * @param right - 第二个代码
 * @returns 任一为空字符串时返回 false；否则比较规范化键
 */
export function areStockCodesEquivalent(left: string, right: string): boolean {
  if (!left.trim() || !right.trim()) return false;
  return stockCodeMatchKey(left) === stockCodeMatchKey(right);
}

/**
 * 在代码列表中查找与给定代码等价的首个代码。
 *
 * @param codes - 候选代码数组
 * @param stockCode - 目标代码
 * @returns 找到则返回匹配的代码，否则返回 undefined
 */
export function findMatchingStockCode(codes: string[], stockCode: string): string | undefined {
  if (!stockCode.trim()) return undefined;
  const targetKey = stockCodeMatchKey(stockCode);
  return codes.find((code) => code.trim() && stockCodeMatchKey(code) === targetKey);
}

/**
 * 判断代码列表是否包含与给定代码等价的股票。
 *
 * @param codes - 候选代码数组
 * @param stockCode - 目标代码
 * @returns 包含则返回 true
 */
export function includesStockCode(codes: string[], stockCode: string): boolean {
  return findMatchingStockCode(codes, stockCode) !== undefined;
}
