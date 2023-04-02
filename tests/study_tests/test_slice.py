def test_array_reverse():
    arr = [1, 2, 3]
    reversed_arr = arr.copy()
    reversed_arr.reverse()
    assert (reversed_arr[0] == 3)

    reversed_arr = [item for item in reversed(arr)]
    assert (reversed_arr[0] == 3)
