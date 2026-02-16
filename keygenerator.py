from cryptography.fernet import Fernet

key = Fernet.generate_key()

print(key)          # например: b'g8k9...=='
print(key.decode()) # строка для копирования: g8k9...==