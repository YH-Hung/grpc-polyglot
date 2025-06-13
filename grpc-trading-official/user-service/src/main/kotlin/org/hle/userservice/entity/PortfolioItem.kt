package org.hle.userservice.entity

import org.hle.common.Ticker
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.Id

@Entity
class PortfolioItem {

    @Id
    @GeneratedValue
    var id: Int? = null

    @Column(name = "customer_id")
    var userId: Int? = null
    var ticker: Ticker? = null
    var quantity: Int? = null
}