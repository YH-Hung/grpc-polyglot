package org.hle.user.tests;

import org.hle.common.Ticker;
import org.hle.user.StockTradeRequest;
import org.hle.user.TradeAction;
import org.hle.user.UserInformationRequest;
import org.hle.user.UserServiceGrpc;
import io.grpc.Status;
import io.grpc.StatusRuntimeException;
import net.devh.boot.grpc.client.inject.GrpcClient;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(properties = {
        "grpc.server.port=-1",
        "grpc.server.in-process-name=integration-test",
        "grpc.client.user-service.address=in-process:integration-test"
})
public class UserServiceTest {

    @GrpcClient("user-service")
    private UserServiceGrpc.UserServiceBlockingStub stub;

    @Test
    public void userInformationTest() {
        var request = UserInformationRequest.newBuilder()
                .setUserId(1)
                .build();
        var response = this.stub.getUserInformation(request);

        Assertions.assertEquals(10_000, response.getBalance());
        Assertions.assertEquals("Sam", response.getName());
        Assertions.assertTrue(response.getHoldingsList().isEmpty());
    }

    @Test
    public void unknownUserTest() {
        var ex = Assertions.assertThrows(StatusRuntimeException.class, () -> {
            var request = UserInformationRequest.newBuilder()
                    .setUserId(5)
                    .build();
            var response = this.stub.getUserInformation(request);
        });

        Assertions.assertEquals(Status.Code.NOT_FOUND, ex.getStatus().getCode());
    }

    @Test
    public void unknownTickerBuyTest() {
        var ex = Assertions.assertThrows(StatusRuntimeException.class, () -> {
            var request = StockTradeRequest.newBuilder()
                    .setUserId(1)
                    .setPrice(1)
                    .setQuantity(2)
                    .setAction(TradeAction.BUY)
                    .build();
            var response = this.stub.tradeStock(request);
        });

        Assertions.assertEquals(Status.Code.INVALID_ARGUMENT, ex.getStatus().getCode());
    }

    @Test
    public void insufficientSharesTest() {
        var ex = Assertions.assertThrows(StatusRuntimeException.class, () -> {
            var request = StockTradeRequest.newBuilder()
                    .setUserId(1)
                    .setPrice(1)
                    .setQuantity(1000)
                    .setTicker(Ticker.AMAZON)
                    .setAction(TradeAction.SELL)
                    .build();
            var response = this.stub.tradeStock(request);
        });

        Assertions.assertEquals(Status.Code.FAILED_PRECONDITION, ex.getStatus().getCode());
    }

    @Test
    public void insufficientBalanceTest() {
        var ex = Assertions.assertThrows(StatusRuntimeException.class, () -> {
            var request = StockTradeRequest.newBuilder()
                    .setUserId(1)
                    .setPrice(1000)
                    .setQuantity(1000)
                    .setAction(TradeAction.BUY)
                    .setTicker(Ticker.AMAZON)
                    .build();
            var response = this.stub.tradeStock(request);
        });

        Assertions.assertEquals(Status.Code.FAILED_PRECONDITION, ex.getStatus().getCode());
    }

    @Test
    public void buySellTest() {
        var buyRequest = StockTradeRequest.newBuilder()
                .setUserId(2)
                .setPrice(100)
                .setQuantity(5)
                .setTicker(Ticker.AMAZON)
                .setAction(TradeAction.BUY)
                .build();

        var buyResponse = this.stub.tradeStock(buyRequest);

        Assertions.assertEquals(9500, buyResponse.getBalance());

        var userRequest = UserInformationRequest.newBuilder()
                .setUserId(2)
                .build();

        var userResponse = this.stub.getUserInformation(userRequest);
        Assertions.assertEquals(1, userResponse.getHoldingsCount());
        Assertions.assertEquals(Ticker.AMAZON, userResponse.getHoldings(0).getTicker());

        var sellRequest = buyRequest.toBuilder()
                .setAction(TradeAction.SELL)
                .setPrice(102)
                .build();

        var sellResponse = this.stub.tradeStock(sellRequest);
        Assertions.assertEquals(9500, sellResponse.getBalance());
    }
}
