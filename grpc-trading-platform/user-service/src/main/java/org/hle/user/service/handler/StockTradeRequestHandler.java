package org.hle.user.service.handler;

import org.hle.common.Ticker;
import org.hle.user.StockTradeRequest;
import org.hle.user.StockTradeResponse;
import org.hle.user.exception.InsufficientBalanceException;
import org.hle.user.exception.InsufficientSharesException;
import org.hle.user.exception.UnknownTickerException;
import org.hle.user.exception.UnknownUserException;
import org.hle.user.repository.PortfolioRepository;
import org.hle.user.repository.UserRepository;
import org.hle.user.util.EntityMessageMapper;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

@Service
public class StockTradeRequestHandler {
    private final UserRepository userRepository;
    private final PortfolioRepository portfolioRepository;

    public StockTradeRequestHandler(UserRepository userRepository, PortfolioRepository portfolioRepository) {
        this.userRepository = userRepository;
        this.portfolioRepository = portfolioRepository;
    }

    @Transactional
    public StockTradeResponse buyStock(StockTradeRequest request) {
        validateTicker(request.getTicker());
        var user = userRepository.findById(request.getUserId())
                .orElseThrow(() -> new UnknownUserException(request.getUserId()));

        var totalPrice = request.getPrice() * request.getQuantity();
        validateUserBalance(user.getId(), user.getBalance(), totalPrice);

        user.setBalance(user.getBalance() - totalPrice);
        portfolioRepository.findByUserIdAndTicker(user.getId(), request.getTicker())
                .ifPresentOrElse(item -> item.setQuantity(item.getQuantity() + request.getQuantity()),
                        () -> portfolioRepository.save(EntityMessageMapper.toPortfolioItem(request)));

        return EntityMessageMapper.toStockTradeResponse(request, user.getBalance());
    }

    @Transactional
    public StockTradeResponse sellStock(StockTradeRequest request) {
        validateTicker(request.getTicker());
        var user = userRepository.findById(request.getUserId())
                .orElseThrow(() -> new UnknownUserException(request.getUserId()));

        var portfolio = portfolioRepository.findByUserIdAndTicker(user.getId(), request.getTicker())
                .filter(pi -> pi.getQuantity() >= request.getQuantity())
                .orElseThrow(() -> new InsufficientSharesException(request.getUserId()));

        var totalPrice = request.getPrice() * request.getQuantity();
        user.setBalance(user.getBalance() + totalPrice);
        portfolio.setQuantity(portfolio.getQuantity() - request.getQuantity());

        return EntityMessageMapper.toStockTradeResponse(request, user.getBalance());
    }

    private void validateTicker(Ticker ticker) {
        if (Ticker.UNKNOWN.equals(ticker)) {
            throw new UnknownTickerException();
        }
    }

    private void validateUserBalance(Integer userId, Integer userBalance, Integer totalPrice) {
        if (totalPrice > userBalance) {
            throw new InsufficientBalanceException(userId);
        }
    }
}
