/**
 * @fileoverview 测试页面（CodeTest）
 * 用于开发期功能验证与组件联调，路由地址 /codeTest。
 * @module pages
 */

import React from "react";
import { useState } from 'react';
import { AppPage, Input, HrsButton, Modal } from '../components';
import { Button } from '@heroui/react';
/**
 * 测试页面组件
 * 当前为占位内容，可在开发过程中按需挂载待验证的组件与逻辑。
 */
const CodeTestPage: React.FC = () => {
    // 三个尺寸的输入框共享同一受控值，便于对比 size 参数的视觉效果。
    const [newName] = useState('');
    const [isOpen, setIsOpen] = useState(false);

    const clsickFn = () => {
        console.log('点击了')
    }



    const openModel = () => {
        setIsOpen(true)
        console.log('打开模态框')
    }





    return (
        <AppPage>

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
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                     <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                     <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
                    <p>Modal content</p>
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
