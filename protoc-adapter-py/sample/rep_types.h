#pragma once

struct RepOrderInfo {
    int orderId;
    char instrumentCode[32];
    double quantity;
};

struct RepAccountStatus {
    int accountId;
    double balance;
};

struct OrderRequest {
    int orderId;
    char instrumentCode[32];
    double quantity;
};
