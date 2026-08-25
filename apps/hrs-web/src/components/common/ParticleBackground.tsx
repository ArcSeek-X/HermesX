/**
 * ===================================
 * 粒子背景组件（ParticleBackground）
 * ===================================
 *
 * 【功能介绍】
 * 一个基于 HTML5 Canvas 的「动态粒子背景」组件。在画布上随机生成若干蓝色调粒子，
 * 粒子缓慢漂浮并在边界反弹；当鼠标靠近时，粒子会与鼠标连线、并被轻微「吸引」扰动，
 *   粒子彼此靠近时也会以细线连接，形成科技感网络效果。整个背景透明、不拦截鼠标事件
 *   （pointer-events-none），通常作为页面底层装饰。
 *
 * 【设计要点】
 * 1. 粒子模型（Particle）：位置 (x,y)、速度 (vx,vy)、半径、颜色、基础透明度 baseAlpha。
 * 2. 生命周期（useEffect）：
 *    - 初始化：根据画布面积按比例生成粒子数量（面积/10000），自适应屏幕大小；
 *    - 动画循环：requestAnimationFrame 驱动 update（移动+边界反弹）→ draw（粒子）→
 *      drawLines（鼠标连线 + 粒子互连）；
 *    - 事件绑定：resize 重算尺寸与粒子、mousemove 更新鼠标坐标、mouseout 重置鼠标到屏外；
 *    - 清理：卸载时移除监听并 cancelAnimationFrame，避免内存/帧率泄漏。
 * 3. 鼠标交互：距离 <250px 时与鼠标连线并施加吸引力；粒子两两距离 <150px 时彼此连线。
 * 4. 性能取舍：粒子数量随屏幕面积线性增长，连线为 O(n²) 但受距离阈值与数量限制，
 *    适用于装饰场景，不对性能过分敏感。
 *
 * 【使用方式】
 *   <div className="relative">
 *     <ParticleBackground />
 *     <YourContent className="relative z-10" />
 *   </div>
 */

import { useEffect, useRef } from 'react';

/** 单个粒子的数据结构 */
type Particle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  baseAlpha: number;
};

/** 粒子配色池（RGB 字符串，便于拼 rgba） */
const PARTICLE_COLORS = ['59, 130, 246', '37, 99, 235', '96, 165, 250', '99, 102, 241'];

/** 创建一个随机粒子（位置、速度、半径、颜色、透明度均在合理范围内随机） */
function createParticle(canvas: HTMLCanvasElement): Particle {
  return {
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    vx: (Math.random() - 0.5) * 0.5,
    vy: (Math.random() - 0.5) * 0.5,
    radius: Math.random() * 2.0 + 1.0,
    color: PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)],
    baseAlpha: Math.random() * 0.6 + 0.2,
  };
}

/** 更新粒子位置，并在撞到画布边界时反弹速度分量 */
function updateParticle(particle: Particle, canvas: HTMLCanvasElement) {
  particle.x += particle.vx;
  particle.y += particle.vy;

  if (particle.x < 0 || particle.x > canvas.width) {
    particle.vx *= -1;
  }
  if (particle.y < 0 || particle.y > canvas.height) {
    particle.vy *= -1;
  }
}

/** 绘制单个粒子：实心圆，使用其颜色与 baseAlpha */
function drawParticle(ctx: CanvasRenderingContext2D, particle: Particle) {
  ctx.beginPath();
  ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
  ctx.fillStyle = `rgba(${particle.color}, ${particle.baseAlpha})`;
  ctx.fill();
}

/**
 * 粒子背景组件（无 Props）。
 * 内部通过 canvasRef 持有画布，并在挂载后启动动画；卸载时自动清理。
 */
export const ParticleBackground = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let particles: Particle[] = [];
    const mouse = { x: -1000, y: -1000 };

    // 重算画布尺寸并按面积重新生成粒子
    const resize = () => {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      initParticles();
    };

    // 按画布面积初始化粒子集合
    const initParticles = () => {
      if (!canvas) return;
      particles = [];
      const numParticles = Math.floor((canvas.width * canvas.height) / 10000);
      for (let i = 0; i < numParticles; i++) {
        particles.push(createParticle(canvas));
      }
    };

    // 绘制连线：粒子与鼠标、粒子与粒子之间的近距连线
    const drawLines = (c: CanvasRenderingContext2D) => {
      for (let i = 0; i < particles.length; i++) {
        const dxMouse = particles[i].x - mouse.x;
        const dyMouse = particles[i].y - mouse.y;
        const distMouse = Math.sqrt(dxMouse * dxMouse + dyMouse * dyMouse);

        // 与鼠标的连线 + 吸引力扰动（距离 <250）
        if (distMouse > 0 && distMouse < 250) {
          c.beginPath();
          const opacity = 0.8 * (1 - distMouse / 250);
          c.strokeStyle = `rgba(59, 130, 246, ${opacity})`;
          c.lineWidth = 2.0;
          c.moveTo(particles[i].x, particles[i].y);
          c.lineTo(mouse.x, mouse.y);
          c.stroke();

          const force = (250 - distMouse) / 250;
          particles[i].x += (dxMouse / distMouse) * force * 2.0;
          particles[i].y += (dyMouse / distMouse) * force * 2.0;
        }

        // 粒子两两近距连线（距离 <150）
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 150) {
            c.beginPath();
            const opacity = 0.3 * (1 - dist / 150);
            c.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
            c.lineWidth = 0.8;
            c.moveTo(particles[i].x, particles[i].y);
            c.lineTo(particles[j].x, particles[j].y);
            c.stroke();
          }
        }
      }
    };

    // 每帧：清空画布 → 更新并绘制粒子 → 绘制连线 → 申请下一帧
    const animate = () => {
      if (!canvas || !ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((particle) => {
        updateParticle(particle, canvas);
        drawParticle(ctx, particle);
      });
      drawLines(ctx);

      animationFrameId = requestAnimationFrame(animate);
    };

    const handleResize = () => resize();
    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    const handleMouseOut = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    // 绑定窗口事件
    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseout', handleMouseOut);

    // 启动
    resize();
    animate();

    // 卸载清理：移除监听 + 取消动画帧
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseout', handleMouseOut);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    // 绝对定位铺满父容器、置于最底层、不拦截鼠标事件
    <canvas
      ref={canvasRef}
      className="absolute inset-0 z-0 pointer-events-none"
      style={{ background: 'transparent' }}
    />
  );
};
