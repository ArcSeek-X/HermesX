package hermesx.system.config;

import org.apache.ibatis.session.SqlSessionFactory;
import org.mybatis.spring.MyBatisExceptionTranslator;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.support.SQLExceptionSubclassTranslator;
import org.springframework.dao.DuplicateKeyException;
import org.sqlite.SQLiteException;
import org.sqlite.SQLiteErrorCode;

/** MyBatis 的会话适配配置：共享 Spring 事务，并把厂商错误转成业务层可识别的异常。 */
@Configuration
public class DatabaseConfig {
    @Bean SqlSessionTemplate sqlSessionTemplate(SqlSessionFactory factory) {
        var fallback = new SQLExceptionSubclassTranslator();
        var translator = new MyBatisExceptionTranslator(() -> (task, sql, error) -> {
            // 准确识别唯一键冲突；不能把锁冲突、SQL 错误等都谎报为重复账号。
            if (error instanceof SQLiteException sqlite
                    && sqlite.getResultCode() == SQLiteErrorCode.SQLITE_CONSTRAINT_UNIQUE) {
                return new DuplicateKeyException("登录账号已存在", error);
            }
            return fallback.translate(task, sql, error);
        }, true);
        return new SqlSessionTemplate(factory, factory.getConfiguration().getDefaultExecutorType(), translator);
    }
}
