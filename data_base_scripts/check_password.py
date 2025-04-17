from werkzeug.security import check_password_hash

stored_hash = 'scrypt:32768:8:1$E3zEjm9pKrvHPq9E$1e4abfc7bc472f13487ed570a9bedc2c99d0ddc87f5433542f61042d8dec926fedccef789045b219854f6abc7570cba954964af1ad15e2b2096ee9e2fc093f87'
password = 'Aruba@123'
print(check_password_hash(stored_hash, password))  # Likely prints False