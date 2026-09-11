from app.rbac import ROLE_COLLECTIONS, can_access_collection, get_role_access


def test_role_access_matrix():
    assert can_access_collection('doctor', 'clinical') is True
    assert can_access_collection('doctor', 'billing') is False
    assert can_access_collection('admin', 'billing') is True


def test_role_access_summary():
    assert 'general' in get_role_access('nurse')
    assert 'billing' not in get_role_access('nurse')
    assert 'equipment' in get_role_access('technician')


def test_access_matrix_complete():
    assert ROLE_COLLECTIONS['doctor'] == ['general', 'clinical', 'nursing']
    assert ROLE_COLLECTIONS['admin'] == ['general', 'clinical', 'nursing', 'billing', 'equipment']
