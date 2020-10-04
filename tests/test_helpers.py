from aioasuswrt.helpers import convert_size


def test_convert_size():
    assert "0 B" == convert_size(0)
    assert "1.0 B" == convert_size(1)
    assert "1.0 KB" == convert_size(1024)
    assert "1.0 MB" == convert_size(1024 * 1024)
    assert "1.0 GB" == convert_size(1024 * 1024 * 1024)
