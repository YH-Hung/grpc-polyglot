package org.hle.aggregator.controller;

import org.hle.aggregator.service.TradeService;
import org.hle.user.StockTradeRequest;
import org.hle.user.StockTradeResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("trade")
public class TradeController {

    @Autowired
    private TradeService tradeService;

    @PostMapping(produces = MediaType.APPLICATION_JSON_VALUE)
    public StockTradeResponse trade(@RequestBody StockTradeRequest request) {
        return this.tradeService.trade(request);
    }
}
