package org.hle.userservice.repository

import org.hle.userservice.entity.User
import org.springframework.data.repository.CrudRepository

interface UserRepository : CrudRepository<User, Int> {
}