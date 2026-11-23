package hermesx.common.rest;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class RestResultTest {
    @Test void independentSuccessObjectsCannotPolluteOneAnother() {
        var first=RestResult.success("first");
        var second=RestResult.success("second");
        assertNotSame(first,second);
        assertEquals("first",first.resultData()); assertEquals("second",second.resultData());
        assertEquals("200",first.resultCode()); assertEquals("操作成功。",first.resultMsg());
    }
    @Test void failuresCarryNoBusinessDataAndAllowSafeSpecificMessages() {
        var failure=RestResult.failure(ResultCodeEnum.INVALID_REQUEST,"名称不能为空。");
        assertEquals("INVALID_REQUEST",failure.resultCode()); assertNull(failure.resultData());
        assertEquals("名称不能为空。",failure.resultMsg());
        assertEquals(ResultCodeEnum.NOT_FOUND.getMessage(),RestResult.failure(ResultCodeEnum.NOT_FOUND).resultMsg());
    }
    @Test void invalidContractIsRejected() {
        assertThrows(IllegalArgumentException.class,()->RestResult.failure(ResultCodeEnum.SUCCESS));
        assertThrows(IllegalArgumentException.class,()->new RestResult<>(" ","message",null));
        assertThrows(NullPointerException.class,()->new RestResult<>("code",null,null));
    }
}
