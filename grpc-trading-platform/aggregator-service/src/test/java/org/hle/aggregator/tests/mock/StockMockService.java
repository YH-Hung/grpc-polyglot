package org.hle.aggregator.tests.mock;

import com.google.common.util.concurrent.Uninterruptibles;
import com.google.protobuf.Empty;
import com.vinsguru.common.Ticker;
import io.grpc.stub.StreamObserver;
import org.hle.stock.PriceUpdate;
import org.hle.stock.StockPriceRequest;
import org.hle.stock.StockPriceResponse;
import org.hle.stock.StockServiceGrpc;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.TimeUnit;

public class StockMockService extends StockServiceGrpc.StockServiceImplBase {

    private static final Logger log = LoggerFactory.getLogger(StockMockService.class);

    @Override
    public void getStockPrice(StockPriceRequest request, StreamObserver<StockPriceResponse> responseObserver) {
        var response = StockPriceResponse.newBuilder()
                .setPrice(15)
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getPriceUpdates(Empty request, StreamObserver<PriceUpdate> responseObserver) {
        Uninterruptibles.sleepUninterruptibly(3, TimeUnit.SECONDS);

        for (int i = 0; i < 5; i++) {
            var priceUpdate = PriceUpdate.newBuilder()
                    .setPrice(i + 1)
                    .setTicker(Ticker.AMAZON)
                    .build();

            log.info("Price update: {}", priceUpdate);
            responseObserver.onNext(priceUpdate);
        }

        responseObserver.onCompleted();
    }
}
