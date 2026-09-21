/**
 * useAuth —— 鉴权钩子的统一出口。
 * 实际实现位于 stores/AuthStore（Zustand），此处仅做一层转发（re-export），
 * 让业务组件可从 hooks 包统一引入，降低对 store 内部路径的耦合。
 */
export { useAuthStore as useAuth } from '../stores/AuthStore';
