#pragma once

/* Simple type aliases */
typedef int UserId;
typedef double Price;
typedef long Timestamp;

/* Top-level anonymous typedef struct */
typedef struct {
    UserId id;
    char venue[64];
    Price fillPrice;
    int fillQuantity;
    Timestamp fillTime;
} ExecutionReport;

/* Named struct with nested anonymous structs and type aliases */
struct AdvancedOrder {
    int orderId;
    char instrumentCode[32];
    Price quantity;
    Price unitPrice;
    bool isBuy;
    struct {
        UserId oderId;
        char traderName[64];
    } traderInfo;
    struct {
        char feeType[32];
        Price amount;
    } fee;
    ExecutionReport execution;
};
