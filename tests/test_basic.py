def test_package_imports():
    """Test that the package can be imported successfully."""
    import rentry

    assert hasattr(rentry, "RentrySyncClient")
