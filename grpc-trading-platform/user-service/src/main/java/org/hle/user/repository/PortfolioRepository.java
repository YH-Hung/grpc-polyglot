package org.hle.user.repository;

import org.hle.common.Ticker;
import org.hle.user.entity.PortfolioItem;
import org.springframework.data.repository.CrudRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface PortfolioRepository extends CrudRepository<PortfolioItem, Integer> {

    List<PortfolioItem> findAllByUserId(Integer userId);
    Optional<PortfolioItem> findByUserIdAndTicker(Integer userId, Ticker ticker);
}
