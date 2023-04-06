def test_python_loop():
    r = 0
    count = 0
    first = 0
    val = 0
    for i in range(10):
        val += 1
        if count == 0:
            first = val
        r += val
        count += 1
    assert first == 1
    assert count == 10
    assert r == 55
