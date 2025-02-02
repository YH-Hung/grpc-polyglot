package org.hle.aggregator.service;

import org.hle.user.UserInformation;
import org.hle.user.UserInformationRequest;
import org.hle.user.UserServiceGrpc;
import net.devh.boot.grpc.client.inject.GrpcClient;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    @GrpcClient("user-service")
    private UserServiceGrpc.UserServiceBlockingStub userClient;

    public UserInformation getUserInformation(int userId) {
        var request = UserInformationRequest.newBuilder()
                .setUserId(userId)
                .build();

        return userClient.getUserInformation(request);
    }

}
