package org.hle.userservice.util

import org.hle.userservice.entity.User
import org.hle.userservice.entity.PortfolioItem
import org.hle.user.Holding
import org.hle.user.StockTradeRequest
import org.hle.user.StockTradeResponse
import org.hle.user.UserInformation

object EntityMessageMapper {
    fun toUserInformation(user: User, items: kotlin.collections.MutableList<PortfolioItem?>): UserInformation {
        val holding = items.stream()
            .map<Holding?> { i: PortfolioItem? ->
                Holding.newBuilder()
                    .setTicker(i?.ticker)
                    .setQuantity(i?.quantity ?: 0)
                    .build()
            }
            .toList()

        return UserInformation.newBuilder()
            .setUserId(user.id ?: 0)
            .setName(user.name)
            .setBalance(user.balance ?: 0)
            .addAllHoldings(holding)
            .build()
    }

    fun toPortfolioItem(request: StockTradeRequest): PortfolioItem {
        val item: PortfolioItem = PortfolioItem()
        item.userId = request.getUserId()
        item.ticker = request.getTicker()
        item.quantity = request.getQuantity()

        return item
    }

    fun toStockTradeResponse(request: StockTradeRequest, balance: kotlin.Int): StockTradeResponse {
        return StockTradeResponse.newBuilder()
            .setUserId(request.getUserId())
            .setPrice(request.getPrice())
            .setTicker(request.getTicker())
            .setQuantity(request.getQuantity())
            .setAction(request.getAction())
            .setTotalPrice(request.getPrice() * request.getQuantity())
            .setBalance(balance)
            .build()
    }
}
