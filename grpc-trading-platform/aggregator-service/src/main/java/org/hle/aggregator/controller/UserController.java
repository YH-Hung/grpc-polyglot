package org.hle.aggregator.controller;

import org.hle.aggregator.service.UserService;
import org.hle.user.UserInformation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("user")
public class UserController {
    @Autowired
    private UserService userService;

    @GetMapping(value = "{userId}", produces = MediaType.APPLICATION_JSON_VALUE)
    public UserInformation getUserInformation(@PathVariable Integer userId) {
        // Need to assign the produce media type because UserInformation is a proto message.
        return this.userService.getUserInformation(userId);
    }

}
