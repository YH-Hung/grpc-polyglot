package org.hle.userservice.handler

import org.hle.user.UserInformation
import org.hle.user.UserInformationRequest
import org.hle.userservice.entity.User
import org.hle.userservice.entity.PortfolioItem
import org.hle.userservice.exception.UnknownUserException
import org.hle.userservice.repository.PortfolioItemRepository
import org.hle.userservice.repository.UserRepository
import org.hle.userservice.util.EntityMessageMapper
import org.springframework.stereotype.Service

@Service
class UserInformationRequestHandler(private val userRepository: UserRepository,
                                    private val portfolioRepository: PortfolioItemRepository
) {

    fun getUserInformation(request: UserInformationRequest): UserInformation {
        val user: User =
            userRepository.findById(request.getUserId())
                .orElseThrow { UnknownUserException(request.getUserId()) }

        val portfolioItems: List<PortfolioItem> =
            portfolioRepository.findByUserId(user.id!!)

        return EntityMessageMapper.toUserInformation(user, portfolioItems.toMutableList())
    }
}
