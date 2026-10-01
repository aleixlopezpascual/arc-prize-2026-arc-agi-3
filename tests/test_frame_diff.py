from src.perception.frame_diff import compute_frame_diff


def test_frame_diff_moved_and_changed_color():
    # 5x5 board: object 1 moves down, object 2 changes color from 3 to 4
    before = [
        [1, 1, 0, 3, 0],
        [1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    after = [
        [0, 0, 0, 4, 0],
        [0, 0, 0, 0, 0],
        [1, 1, 0, 0, 0],
        [1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    diff = compute_frame_diff(before, after, background_color=0)

    assert diff["changed_cell_count"] > 0
    assert len(diff["moved"]) == 1
    assert diff["moved"][0]["color"] == 1
    assert diff["moved"][0]["from_bbox"] == [0, 0, 1, 1]
    assert diff["moved"][0]["to_bbox"] == [2, 0, 3, 1]

    assert len(diff["changed_color"]) == 1
    assert diff["changed_color"][0]["before_color"] == 3
    assert diff["changed_color"][0]["after_color"] == 4


def test_frame_diff_appeared_disappeared():
    before = [[1, 0], [0, 0]]
    after = [[0, 0], [0, 2]]
    diff = compute_frame_diff(before, after, background_color=0)

    assert len(diff["disappeared"]) == 1
    assert diff["disappeared"][0]["color"] == 1
    assert len(diff["appeared"]) == 1
    assert diff["appeared"][0]["color"] == 2


def test_frame_diff_resized():
    # 2x2 square grows to 2x3 rectangle of same color
    before = [
        [1, 1, 0],
        [1, 1, 0],
        [0, 0, 0],
    ]
    after = [
        [1, 1, 1],
        [1, 1, 1],
        [0, 0, 0],
    ]
    diff = compute_frame_diff(before, after, background_color=0)
    assert len(diff["resized"]) == 1
    assert diff["resized"][0]["color"] == 1
    assert diff["resized"][0]["from_bbox"] == [0, 0, 1, 1]
    assert diff["resized"][0]["to_bbox"] == [0, 0, 1, 2]
