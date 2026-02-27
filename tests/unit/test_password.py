from app.utils.password import generate_password, get_password_hash, verify_password


def test_hash_and_verify_password():
    password = "my_secret_password"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True


def test_verify_wrong_password():
    hashed = get_password_hash("correct_password")
    assert verify_password("wrong_password", hashed) is False


def test_generate_password_length():
    for length in (8, 12, 20):
        pwd = generate_password(length=length)
        assert len(pwd) == length


def test_generate_password_uniqueness():
    pwd1 = generate_password()
    pwd2 = generate_password()
    assert pwd1 != pwd2
