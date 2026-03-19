from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hash_val = "$2b$12$sG70L5u9qjruQ75/1KlqnOmjut5DRlr0kBQjaIU54VK3XKpnghUKa"
print(f"Verifying 'admin123' against {hash_val}")
print(pwd_context.verify("admin123", hash_val))
