from ghoshell.contracts import Meta


def test_meta_new_instance():
    meta = Meta(id="id", kind="kind")
    assert meta.config is not None
