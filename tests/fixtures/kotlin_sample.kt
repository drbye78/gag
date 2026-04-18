// Kotlin data class example
data class User(
    val id: Long,
    val name: String,
    val email: String,
    val createdAt: Instant = Instant.now()
)

// Kotlin sealed class
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String) : Result<Nothing>()
    object Loading : Result<Nothing>()
}

// Kotlin interface
interface Repository<T> {
    suspend fun getById(id: Long): T?
    suspend fun getAll(): List<T>
    suspend fun save(entity: T): T
    suspend fun delete(id: Long): Boolean
}

// Kotlin object (singleton)
object UserManager {
    private val users = mutableMapOf<Long, User>()
    
    fun getUser(id: Long): User? = users[id]
    
    fun addUser(user: User) {
        users[user.id] = user
    }
}

// Kotlin suspend function
suspend fun fetchUser(id: Long): User? {
    delay(100)
    return User(id, "User $id", "user$id@example.com")
}

// Kotlin regular function
fun calculateSum(a: Int, b: Int): Int = a + b

// Kotlin enum
enum class Role {
    ADMIN,
    USER,
    GUEST
}