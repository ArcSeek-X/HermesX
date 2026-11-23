package hermesx.system;

import hermesx.system.config.NacosRegistrationConfig;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import static org.assertj.core.api.Assertions.*;

/** 配置错误应在注册前明确失败；不需要网络或真实Nacos。 */
class NacosRegistrationConfigTest {
    private final ApplicationContextRunner context = new ApplicationContextRunner()
            .withUserConfiguration(NacosRegistrationConfig.class);

    @Test void disabledDoesNotRequireRegistry() {
        context.withPropertyValues("spring.cloud.nacos.discovery.enabled=false")
                .run(c -> assertThat(c).hasNotFailed().doesNotHaveBean(NacosRegistrationConfig.class));
    }

    @Test void enabledRequiresAddressAndNonPublicNamespaceAndReachableIp() {
        String prefix = "spring.cloud.nacos.discovery.";
        for (String[] properties : new String[][] {
            {prefix + "enabled=true"},
            {prefix + "enabled=true", prefix + "server-addr=localhost:8848"},
            {prefix + "enabled=true", prefix + "server-addr=localhost:8848", prefix + "namespace=public"},
            {prefix + "enabled=true", prefix + "server-addr=localhost:8848", prefix + "namespace=test", prefix + "ip=0.0.0.0"}
        }) {
            context.withPropertyValues(properties).run(c -> assertThat(c).hasFailed());
        }
    }

    @Test void explicitNamespaceIsAccepted() {
        context.withPropertyValues("spring.cloud.nacos.discovery.enabled=true",
                "spring.cloud.nacos.discovery.server-addr=localhost:8848",
                "spring.cloud.nacos.discovery.namespace=test-namespace",
                "spring.cloud.nacos.discovery.ip=127.0.0.1")
                .run(c -> assertThat(c).hasNotFailed().hasSingleBean(NacosRegistrationConfig.class));
    }
}
