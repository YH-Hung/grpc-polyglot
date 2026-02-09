#pragma once

struct TradeExecution {
    long executionId;
    char executionVenue[64];
    double fillPrice;
    int fillQuantity;
};

struct TradeFee {
    char feeType[32];
    double amount;
};

struct TradeOrder {
    int orderId;
    char instrumentCode[32];
    double quantity;
    double unitPrice;
    bool isBuy;
    char traderName[64];
    TradeExecution execution;
    TradeFee fees[20];
};

struct AccountInfo {
    int accountId;
    char accountName[128];
    char accountType[32];
    double balance;
};
