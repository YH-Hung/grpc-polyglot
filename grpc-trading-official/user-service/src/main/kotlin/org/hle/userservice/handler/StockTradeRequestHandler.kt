package org.hle.userservice.handler

import jakarta.transaction.Transactional
import org.hle.common.Ticker
import org.hle.user.StockTradeRequest
import org.hle.user.StockTradeResponse
import org.hle.userservice.entity.User
import org.hle.userservice.exception.InsufficientBalanceException
import org.hle.userservice.exception.InsufficientSharesException
import org.hle.userservice.exception.UnknownTickerException
import org.hle.userservice.exception.UnknownUserException
import org.hle.userservice.repository.PortfolioItemRepository
import org.hle.userservice.repository.UserRepository
import org.hle.userservice.util.EntityMessageMapper
import org.springframework.stereotype.Service

@Service
class StockTradeRequestHandler(private val userRepository: UserRepository,
                               private val portfolioRepository: PortfolioItemRepository
) {

    @Transactional
    fun buyStock(request: StockTradeRequest): StockTradeResponse {
        validateTicker(request.getTicker())
        val user: User =
            userRepository.findById(request.getUserId())
                .orElseThrow({ UnknownUserException(request.getUserId()) })

        val totalPrice: kotlin.Int = request.getPrice() * request.getQuantity()
        validateUserBalance(user.id, user.balance, totalPrice)

        user.balance = user.balance?.minus(totalPrice)
        portfolioRepository.findByUserIdAndTicker(user.id!!, request.getTicker())
            .ifPresentOrElse(
                { item -> item.quantity = item.quantity?.plus(request.getQuantity()) },
                { portfolioRepository.save(EntityMessageMapper.toPortfolioItem(request)) })

        return EntityMessageMapper.toStockTradeResponse(request, user.balance!!)
    }

    @Transactional
    fun sellStock(request: StockTradeRequest): StockTradeResponse {
        validateTicker(request.getTicker())
        val user: User =
            userRepository.findById(request.getUserId())
                .orElseThrow { UnknownUserException(request.getUserId()) }

        val portfolio =
            portfolioRepository.findByUserIdAndTicker(user.id!!, request.getTicker())
                .filter { pi -> pi.quantity!! >= request.getQuantity() }
                .orElseThrow { InsufficientSharesException(request.getUserId()) }

        val totalPrice: kotlin.Int = request.getPrice() * request.getQuantity()
        user.balance = user.balance?.plus(totalPrice)
        portfolio.quantity = portfolio.quantity?.minus(request.getQuantity())

        return EntityMessageMapper.toStockTradeResponse(request, user.balance!!)
    }

    private fun validateTicker(ticker: Ticker?) {
        if (Ticker.UNKNOWN == ticker) {
            throw UnknownTickerException
        }
    }

    private fun validateUserBalance(userId: kotlin.Int?, userBalance: kotlin.Int?, totalPrice: kotlin.Int) {
        if (userBalance == null || totalPrice > userBalance) {
            throw InsufficientBalanceException(userId)
        }
    }
}
