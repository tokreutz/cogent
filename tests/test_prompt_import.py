def test_import_exposes_init():
    import main
    assert hasattr(main, 'init_prompt_session'), 'init_prompt_session not found'
    assert hasattr(main, 'get_user_input'), 'get_user_input not found'
