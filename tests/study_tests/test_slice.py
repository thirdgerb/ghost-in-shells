def test_array_reverse():
    arr = [1, 2, 3]
    reversed_arr = arr.copy()
    reversed_arr.reverse()
    assert (reversed_arr[0] == 3)

    reversed_arr = [item for item in reversed(arr)]
    assert (reversed_arr[0] == 3)


def test_array_append():
    arr = list([2, 5, 3])
    arr.append(4)  # 不需要增加 receiver
    assert len(arr) == 4
    assert arr.pop() == 4
    assert len(arr) == 3


def test_slice_insert():
    arr = list([2, 5, 3])
    arr.insert(0, 6)
    assert arr[0] == 6
    assert len(arr) == 4
