package org.hle.aggregator.service;

import org.hle.stock.StockPriceRequest;
import org.hle.stock.StockServiceGrpc;
import org.hle.user.StockTradeRequest;
import org.hle.user.StockTradeResponse;
import org.hle.user.UserServiceGrpc;
import net.devh.boot.grpc.client.inject.GrpcClient;
import org.springframework.stereotype.Service;

@Service
public class TradeService {

    @GrpcClient("user-service")
    private UserServiceGrpc.UserServiceBlockingStub userClient;

    @GrpcClient("stock-service")
    private StockServiceGrpc.StockServiceBlockingStub stockClient;

    public StockTradeResponse trade(StockTradeRequest request) {
        var priceRequest = StockPriceRequest.newBuilder()
                .setTicker(request.getTicker())
                .build();

        var priceResponse = stockClient.getStockPrice(priceRequest);
        var tradeRequest = request.toBuilder()
                .setPrice(priceResponse.getPrice())
                .build();

        return userClient.tradeStock(tradeRequest);
    }
}
