from werkzeug.security import generate_password_hash
print(generate_password_hash('testpass234', method='pbkdf2:sha256'))