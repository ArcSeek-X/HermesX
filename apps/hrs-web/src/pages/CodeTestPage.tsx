/**
 * @fileoverview 测试页面（CodeTest）
 * 用于开发期功能验证与组件联调，路由地址 /codeTest。
 * @module pages
 */

import React from "react";
import { useState } from 'react';
import { AppPage, Input, HrsButton, Modal, Chip } from '../components';
import { Button } from '@heroui/react';
import { Star, ArrowRight } from '@gravity-ui/icons';
import { showErrorToast, type ToastPlacement } from '../components/basic/Toast';
/**
 * 测试页面组件
 * 当前为占位内容，可在开发过程中按需挂载待验证的组件与逻辑。
 */
const CodeTestPage: React.FC = () => {
    // 三个尺寸的输入框共享同一受控值，便于对比 size 参数的视觉效果。
    const [newName] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    // Chip 关闭演示：受控标签列表
    const [chips, setChips] = useState<string[]>([
        '科创50',
        '人工智能',
        '新能源',
        '港股通',
    ]);

    const clsickFn = () => {
        console.log('点击了')
    }



    const openModel = () => {
        setIsOpen(true)
        console.log('打开模态框')
    }





    return (
        <AppPage>

          {/* ============ 错误 Toast（浮层）组件演示 ============ */}
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <h3 className="text-sm font-medium text-primary-text">错误 Toast（浮层）组件演示</h3>
                <p className="text-xs text-muted">
                    命令式触发，应用根（App.tsx）已挂载一次 {'<Toast />'} 宿主。点击按钮在视口对应角落弹出 danger 浮层，默认 6s 自动消失。
                </p>
                <div className="flex flex-wrap items-center gap-2">
                    {(['top start', 'top', 'top end', 'bottom start', 'bottom', 'bottom end'] as ToastPlacement[]).map((placement) => (
                        <HrsButton
                            key={placement}
                            variant="danger"
                            size="sm"
                            onClick={() =>
                                showErrorToast(
                                    {
                                        title: `错误提示（${placement}）`,
                                        message: '这是一段用户友好的错误描述文案。',
                                        rawMessage: 'Raw server error: 500 Internal Server Error at /api/v1/watchlist',
                                        status: 500,
                                        category: 'unknown',
                                    },
                                    placement
                                )
                            }
                        >
                            {placement}
                        </HrsButton>
                    ))}
                </div>
            </div>


            {/* ============ Chip 组件演示 ============ */}
            <div className="flex flex-col gap-5 rounded-lg border border-border/70 bg-card/75 p-6">
                <h3 className="text-sm font-medium text-primary-text">Chip 组件演示</h3>

                {/* 1. color × variant 矩阵 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">color × variant 矩阵</span>
                    <div className="flex flex-col gap-2">
                        {/* 列头：color 名称 */}
                        <div className="flex flex-wrap items-center gap-2 border-b border-border/40 pb-1">
                            <span className="w-20 shrink-0 text-[11px] font-medium text-muted">variant \ color</span>
                            {(['default', 'accent', 'success', 'warning', 'danger', 'blue', 'purple', 'indigo'] as const).map((color) => (
                                <span key={color} className="w-[3.25rem] shrink-0 text-center text-[11px] font-medium text-muted">
                                    {color}
                                </span>
                            ))}
                        </div>
                        {(['primary', 'secondary', 'tertiary', 'soft'] as const).map((variant) => (
                            <div key={variant} className="flex flex-wrap items-center gap-2">
                                <span className="w-20 shrink-0 text-[11px] text-muted">{variant}</span>
                                {(['default', 'accent', 'success', 'warning', 'danger', 'blue', 'purple', 'indigo'] as const).map((color) => (
                                    <Chip key={color} variant={variant} color={color} className="w-[3.25rem] justify-center">
                                        {color}
                                    </Chip>
                                ))}
                            </div>
                        ))}
                    </div>
                </div>

                {/* 2. 尺寸 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">size</span>
                    <div className="flex flex-wrap items-center gap-2">
                        <Chip size="xs" color="accent">xs尺寸</Chip>
                        <Chip size="sm" color="accent">sm尺寸</Chip>
                        <Chip size="md" color="accent">md尺寸</Chip>
                        <Chip size="lg" color="accent">lg尺寸</Chip>
                        <Chip size="xl" color="accent">xl尺寸</Chip>
                    </div>
                </div>

                {/* 3. 圆角 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">radius</span>
                    <div className="flex flex-wrap items-center gap-2">
                        <Chip radius="full" color="success">full</Chip>
                        <Chip radius="sm" color="success">sm</Chip>
                        <Chip radius="md" color="success">md</Chip>
                        <Chip radius="lg" color="success">lg</Chip>
                    </div>
                </div>

                {/* 4. children 内容（图标、文字由调用方组合） */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">children（图标 + 文字自组合）</span>
                    <div className="flex flex-wrap items-center gap-2">
                        <Chip color="accent">
                            <Star className="h-3.5 w-3.5" />
                            <span>带前缀图标</span>
                        </Chip>
                        <Chip color="warning">
                            <span>带后缀图标</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                        </Chip>
                    </div>
                </div>

                {/* 5. 禁用态 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">isDisabled</span>
                    <div className="flex flex-wrap items-center gap-2">
                        <Chip isDisabled color="danger" variant="soft">禁用标签</Chip>
                    </div>
                </div>

                {/* 6. 关闭按钮（受控交互） */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">onClose（点击 × 移除，受控）</span>
                    <div className="flex flex-wrap items-center gap-2">
                        {chips.length === 0 && <span className="text-xs text-muted">已全部关闭</span>}
                        {chips.map((c) => (
                            <Chip
                                key={c}
                                color="accent"
                                variant="soft"
                                onClose={() => setChips((prev) => prev.filter((x) => x !== c))}
                            >
                                {c}
                            </Chip>
                        ))}
                    </div>
                </div>
            </div>
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <Input
                    aria-label="Search projects"
                    className="w-64 rounded-xl border border-border/80 bg-default text-foreground placeholder:text-muted"
                    placeholder="Search projects..."
                />
            </div>

            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <HrsButton variant="primary" size="sm" onClick={openModel}>
                    Open Modal
                </HrsButton>

                <Modal
                    isOpen={isOpen}
                    onClose={() => {
                        console.log(555555555555)
                        setIsOpen(false);
                    }}
                >
                    <Modal.Header>
                        <Modal.Heading>Modal Title</Modal.Heading>
                        <p className="mt-1 text-sm leading-5 text-muted">这是一段描述文案，用于补充说明弹窗的用途或操作内容。</p>
                    </Modal.Header>
                    <Modal.Body>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                    </Modal.Body>
                    <Modal.Footer>
                        <HrsButton variant="secondary" onClick={() => setIsOpen(false)}>
                            取消
                        </HrsButton>
                        <HrsButton variant="primary" onClick={() => setIsOpen(false)}>
                            确认
                        </HrsButton>
                    </Modal.Footer>
                </Modal>




            </div>
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <Input
                    className="w-100"
                    placeholder="新分组名称（xs）"
                    size="xs"
                    value={newName}

                />
                <Input
                    className="w-200"
                    placeholder="新分组名称（sm）"
                    size="sm"
                    value={newName}
                />
                <Input
                    className="w-full"
                    placeholder="新分组名称（md）"
                    size="md"
                    value={newName}

                />
                <Input
                    placeholder="新分组名称（lg）"
                    size="lg"
                    value={newName}
                />

                <HrsButton variant="primary" size="xs" onClick={clsickFn}>
                    xs - 尺寸按钮 - primary
                </HrsButton>
                <HrsButton variant="secondary" size="sm">
                    sm - 尺寸按钮钮 - secondary
                </HrsButton>
                <HrsButton variant="tertiary" size="xs">
                    xs - 尺寸按钮钮 - tertiary
                </HrsButton>
                <HrsButton variant="outline" size="md">
                    MD - 尺寸按钮钮 - outline
                </HrsButton>
                <HrsButton variant="ghost" size="lg">
                    lg - 尺寸按钮钮 - ghost
                </HrsButton>
                <HrsButton variant="danger" size="lg">
                    lg - 尺寸按钮钮 - danger
                </HrsButton>
                <HrsButton variant="danger-soft" size="xl">
                    xl - 尺寸按钮钮 - danger-soft
                </HrsButton>
                <HrsButton variant="settings-primary" size="sm">
                    sm - 尺寸按钮钮 - ettings-primary
                </HrsButton>
                <HrsButton variant="settings-secondary" size="sm">
                    sm - 尺寸按钮钮 - settings-secondary
                </HrsButton>
                <HrsButton variant="home-action-report" size="sm">
                    sm - 尺寸按钮钮 - home-action-report
                </HrsButton>
                <p>测试</p>

                <Button variant="primary">HeroUI - Primary</Button>
                <Button variant="secondary">HeroUI - secondary</Button>
                <Button variant="tertiary">HeroUI - tertiary</Button>
                <Button variant="outline">HeroUI - outline</Button>
                <Button variant="ghost">HeroUI - ghost</Button>
                <Button variant="danger">HeroUI - danger</Button>
                <Button variant="danger-soft">HeroUI - danger-soft</Button>



            </div>

  


        </AppPage >
    );
};

export default CodeTestPage;
