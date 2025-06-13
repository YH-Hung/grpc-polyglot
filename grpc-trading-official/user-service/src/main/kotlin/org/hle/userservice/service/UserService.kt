package org.hle.userservice.service

import org.hle.user.UserServiceGrpc.UserServiceImplBase
import org.hle.user.UserInformationRequest
import org.hle.user.UserInformation
import org.hle.user.StockTradeRequest
import org.hle.user.StockTradeResponse
import org.hle.user.TradeAction
import org.hle.userservice.handler.UserInformationRequestHandler
import org.hle.userservice.handler.StockTradeRequestHandler
import org.springframework.stereotype.Service

@Service
class UserService(private val userRequestHandler: UserInformationRequestHandler,
                  private val tradeRequestHandler: StockTradeRequestHandler
) :
    UserServiceImplBase() {

    override fun getUserInformation(
        request: UserInformationRequest,
        responseObserver: io.grpc.stub.StreamObserver<UserInformation?>
    ) {
        log.info("user information for id {}", request.getUserId())
        val userInformation: UserInformation =
            this.userRequestHandler.getUserInformation(request)
        responseObserver.onNext(userInformation)
        responseObserver.onCompleted()
    }

    override fun tradeStock(
        request: StockTradeRequest,
        responseObserver: io.grpc.stub.StreamObserver<StockTradeResponse?>
    ) {
        log.info("{}", request)
        val response: StockTradeResponse =
            if (TradeAction.SELL == request.getAction())
                tradeRequestHandler.sellStock(request)
            else
                tradeRequestHandler.buyStock(request)

        responseObserver.onNext(response)
        responseObserver.onCompleted()
    }

    companion object {
        private val log: org.slf4j.Logger = org.slf4j.LoggerFactory.getLogger(UserService::class.java)
    }
}
