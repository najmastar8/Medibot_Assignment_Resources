from app.main import DEMO_USERS


def test_demo_users_count():
    assert len(DEMO_USERS) == 5
    assert 'dr.mehta' in DEMO_USERS
    assert 'admin.sys' in DEMO_USERS
