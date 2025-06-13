package org.hle.userservice.repository

import org.hle.common.Ticker
import org.hle.userservice.entity.PortfolioItem
import org.springframework.data.repository.CrudRepository
import java.util.Optional

interface PortfolioItemRepository : CrudRepository<PortfolioItem, Int> {

    fun findByUserId(userId: Int): List<PortfolioItem>

    fun findByUserIdAndTicker(userId: Int, ticker: Ticker): Optional<PortfolioItem>
}