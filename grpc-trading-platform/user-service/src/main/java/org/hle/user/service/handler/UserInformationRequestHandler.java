package org.hle.user.service.handler;

import org.hle.user.UserInformation;
import org.hle.user.UserInformationRequest;
import org.hle.user.exception.UnknownUserException;
import org.hle.user.repository.PortfolioRepository;
import org.hle.user.repository.UserRepository;
import org.hle.user.util.EntityMessageMapper;
import org.springframework.stereotype.Service;

@Service
public class UserInformationRequestHandler {
    private final UserRepository userRepository;
    private final PortfolioRepository portfolioRepository;

    public UserInformationRequestHandler(UserRepository userRepository, PortfolioRepository portfolioRepository) {
        this.userRepository = userRepository;
        this.portfolioRepository = portfolioRepository;
    }

    public UserInformation getUserInformation(UserInformationRequest request) {
        var user = userRepository.findById(request.getUserId())
                .orElseThrow(() -> new UnknownUserException(request.getUserId()));

        var portfolioItems = portfolioRepository.findAllByUserId(user.getId());

        return EntityMessageMapper.toUserInformation(user, portfolioItems);
    }
}
