package hermesx.system;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/** 只扫描 hermesx.system，启动 system 服务，不会顺带启动 auth 和 analysis。 */
@SpringBootApplication
public class SystemApplication {
    public static void main(String[] args) { SpringApplication.run(SystemApplication.class, args); }
}
