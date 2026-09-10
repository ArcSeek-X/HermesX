/**
 * @fileoverview 组件文档页：HrsCheckbox（复选框）
 * 路由地址 /docs/component/checkbox，菜单名「复选框」。
 * 用于演示 HrsCheckbox 在「多选组」与「单选框」两种模式下的常见用法与状态字段。
 * @module pages
 */

import React, { useState } from 'react';
import { AppPage, HrsCheckbox, type HrsCheckboxSize } from '../../../components';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/**
 * 复选框组件文档演示页。
 *
 * 内部结构固定为 Checkbox → Checkbox.Content → Checkbox.Control → Checkbox.Indicator，
 * 使用方无需关心拼装细节：
 * - 传 options 数组 → 进入「多选组」模式（循环渲染、统一维护选中集合）；
 * - 不传 options → 退化为单个勾选框（HeroUI 原生用法完全一致）。
 */
export const DocsCheckboxPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 受控示例状态
  const [notifyValues, setNotifyValues] = useState<string[]>(['newsletter']);
  const [groupBValues, setGroupBValues] = useState<string[]>(['b']);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [reqGroupValues, setReqGroupValues] = useState<string[]>(['email']);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsCheckbox.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI Checkbox 封装的通用勾选框（HrsCheckbox）。传 options 进入「多选组」模式，不传则退化为单个勾选框；
            原生能力（isDisabled / isReadOnly / isIndeterminate / isRequired / isInvalid 等）全部透传。
          </p>
        </header>

        {/* 1. 多选组（受控）：value 为 string[]，onChange 回传选中项 value 集合 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：多选组（受控）</h2>
          <p className="text-xs text-muted">
            value 为 string[]，onChange 回传选中项的 value 集合（顺序与 options 一致）。
          </p>
          <span className="text-xs text-secondary-text">
            当前选中：{notifyValues.length > 0 ? notifyValues.join(' / ') : '无'}
          </span>
          <HrsCheckbox
            name="notifications"
            value={notifyValues}
            onChange={(next) => setNotifyValues(next as string[])}
            options={[
              { value: 'notifications', label: '开启通知' },
              { value: 'newsletter', label: '订阅周报', defaultSelected: true },
              { value: 'marketing', label: '接收营销资讯' },
              { value: 'sms', label: '短信推送（disabled）', disabled: true },
            ]}
          />
        </section>

        {/* 2. 多选组（非受控）：defaultValue 或 option.defaultSelected 决定初始选中 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：多选组（非受控）</h2>
          <p className="text-xs text-muted">
            不传 value 即非受控，初始选中由 defaultValue 或各 option.defaultSelected 决定，onChange 仍回传最新集合。
          </p>
          <span className="text-xs text-secondary-text">
            当前选中：{groupBValues.length > 0 ? groupBValues.join(' / ') : '无'}
          </span>
          <HrsCheckbox
            value={groupBValues}
            defaultValue={['b']}
            onChange={(next) => setGroupBValues(next as string[])}
            options={[
              { value: 'a', label: '选项 A' },
              { value: 'b', label: '选项 B（defaultValue 命中）' },
              { value: 'c', label: '选项 C（defaultSelected）', defaultSelected: true },
            ]}
          />
        </section>

        {/* 3. 单选框（原生用法）：isSelected + onChange(boolean) */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：单选框（原生 Checkbox 用法）</h2>
          <p className="text-xs text-muted">
            不传 options 时退化为单个勾选框，isSelected 控制选中态，onChange 回传 boolean（与 HeroUI 原生签名一致）。
          </p>
          <HrsCheckbox
            name="terms"
            label="我已阅读并接受《用户协议》"
            value="on"
            isSelected={acceptTerms}
            onChange={(value) => setAcceptTerms(value as boolean)}
          />
        </section>

        {/* 4. size 对比：sm / md / lg */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：尺寸对比（size）</h2>
          <p className="text-xs text-muted">size 支持 sm / md / lg，默认 md，会同时缩放勾选框、图标与文案。</p>
          <div className="flex flex-wrap items-start gap-6">
            {(['sm', 'md', 'lg'] as HrsCheckboxSize[]).map((size) => (
              <HrsCheckbox
                key={size}
                size={size}
                value={`cb-${size}`}
                label={`size=${size}`}
                defaultSelected
              />
            ))}
          </div>
        </section>

        {/* 5. 状态字段：disabled / indeterminate / description / required / invalid */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：状态字段</h2>
          <p className="text-xs text-muted">
            disabled / indeterminate（半选）/ description（说明）/ required（必填星标）/ invalid + errorMessage（校验报错）。
          </p>

          <HrsCheckbox
            name="states"
            options={[
              { value: 'disabled', label: '禁用项（disabled）', disabled: true },
              { value: 'indeterminate', label: '半选项（indeterminate）', indeterminate: true },
              {
                value: 'desc',
                label: '带说明项（description）',
                description: '这是一段辅助说明文本，渲染在选项下方',
                defaultSelected: true,
              },
            ]}
          />

          <div className="flex flex-col gap-2 border-t border-border/60 pt-3">
            <span className="text-[11px] text-muted">required（isRequired，渲染必填星标）</span>
            <HrsCheckbox
              name="required-demo"
              value="agree"
              label="我已阅读并接受《隐私政策》（required）"
              isRequired
              defaultSelected
            />
          </div>

          <div className="flex flex-col gap-2 border-t border-border/60 pt-3">
            <span className="text-[11px] text-muted">
              invalid + errorMessage（多选组必填，取消到 0 项时联动报错；当前选中 {reqGroupValues.length} 项）
            </span>
            <HrsCheckbox
              name="required-group"
              value={reqGroupValues}
              onChange={(next) => setReqGroupValues(next as string[])}
              options={[
                { value: 'email', label: '邮件通知' },
                { value: 'sms', label: '短信通知' },
                { value: 'push', label: '推送通知' },
              ].map((o, i) =>
                reqGroupValues.length === 0
                  ? {
                      ...o,
                      invalid: true,
                      ...(i === 0 ? { errorMessage: '此项为必填，请至少选择一项' } : {}),
                    }
                  : o,
              )}
            />
          </div>
        </section>

        {/* 6. 排列方向：horizontal / vertical */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例六：排列方向（orientation）</h2>
          <p className="text-xs text-muted">orientation 支持 horizontal（默认）与 vertical，控制多选组的排列方向。</p>
          <div className="flex flex-wrap gap-10">
            <div className="flex flex-col gap-2">
              <span className="text-[11px] text-muted">horizontal</span>
              <HrsCheckbox
                orientation="horizontal"
                defaultValue={['a']}
                options={[
                  { value: 'a', label: '选项 A' },
                  { value: 'b', label: '选项 B' },
                ]}
              />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-[11px] text-muted">vertical</span>
              <HrsCheckbox
                orientation="vertical"
                defaultValue={['a']}
                options={[
                  { value: 'a', label: '选项 A' },
                  { value: 'b', label: '选项 B' },
                ]}
              />
            </div>
          </div>
        </section>

        {/* 7. 数量限制：min / max */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例七：数量限制（min / max）</h2>
          <p className="text-xs text-muted">
            min / max 限制多选组可选中的最小 / 最大数量：触达下限后已选项不可取消，触达上限后未选项不可再勾选。
          </p>
          <span className="text-xs text-secondary-text">最多选 2 项（max=2）</span>
          <HrsCheckbox
            name="limit-demo"
            max={2}
            defaultValue={['a', 'b']}
            options={[
              { value: 'a', label: '选项 A' },
              { value: 'b', label: '选项 B' },
              { value: 'c', label: '选项 C（达到上限后锁定）' },
            ]}
          />
        </section>
      </div>
    </AppPage>
  );
};

export default DocsCheckboxPage;
