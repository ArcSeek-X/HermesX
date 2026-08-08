/**
 * useAuth —— 鉴权钩子的统一出口。
 *
 * 实际实现位于 contexts/AuthContext，这里仅做一层转发（re-export），
 * 让业务组件可以从 hooks 包统一引入，降低对 context 内部路径的耦合。
 */
export { useAuth } from '../contexts/AuthContext';
