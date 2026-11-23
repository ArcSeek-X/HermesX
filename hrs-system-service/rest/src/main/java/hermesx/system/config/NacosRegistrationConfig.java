package hermesx.system.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

/** 仅在开启注册时检查配置；离线测试和单机运行无需注册中心。 */
@Configuration
@ConditionalOnProperty(name = "spring.cloud.nacos.discovery.enabled", havingValue = "true")
public class NacosRegistrationConfig {
    public NacosRegistrationConfig(Environment environment) {
        String address = environment.getProperty("spring.cloud.nacos.discovery.server-addr", "");
        String namespace = environment.getProperty("spring.cloud.nacos.discovery.namespace", "");
        if (address.isBlank()) {
            throw new IllegalArgumentException("开启Nacos注册时必须配置HRS_NACOS_SERVER_ADDR");
        }
        // 当前用3.x客户端对接已有2.5.x服务端，必须使用专用命名空间的ID。
        if (namespace.isBlank() || namespace.equals("public")) {
            throw new IllegalArgumentException("请配置专用HRS_NACOS_NAMESPACE ID，不使用public命名空间");
        }
        String ip = environment.getProperty("spring.cloud.nacos.discovery.ip", "");
        if (ip.isBlank() || ip.equals("0.0.0.0") || ip.equals("::")) {
            throw new IllegalArgumentException("HRS_SYSTEM_REGISTER_IP必须是调用方可以访问的实例地址");
        }
    }
}
