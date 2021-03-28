def test_example_resource(example_resource):
    """Check that the example resource was loaded correctly."""
    assert len(example_resource) == 4
    assert example_resource[0]["average"] == 6.29
