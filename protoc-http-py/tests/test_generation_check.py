def test_generation_check():
    # Import the script-style checker and run it under pytest
    import generation_check as gen
    assert gen.main() is True
