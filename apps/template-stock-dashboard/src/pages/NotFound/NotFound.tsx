import { Link, useRouteError } from 'react-router-dom';
import styles from './NotFound.module.css';

export function NotFound() {
  return (
    <div className={styles.container}>
      <h2 className={styles.code}>404</h2>
      <p className={styles.message}>页面不存在或链接已失效</p>
      <Link to="/" className={styles.homeLink}>
        返回首页
      </Link>
    </div>
  );
}

export function RouteErrorFallback() {
  const error = useRouteError();
  console.error('Route error:', error);
  const message = error instanceof Error ? error.message : '页面加载出错';

  return (
    <div className={styles.container}>
      <h2 className={styles.code}>出错了</h2>
      <p className={styles.message}>{message}</p>
      <Link to="/" className={styles.homeLink} reloadDocument>
        返回首页
      </Link>
    </div>
  );
}
