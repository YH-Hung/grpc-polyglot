package org.hle.userservice.entity

import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.Table

@Entity
@Table(name = "customer")
class User {
    @Id
    var id: Int? = null
    var name: String? = null
    var balance: Int? = null
}
