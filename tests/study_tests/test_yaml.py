import yaml


def test_load_1():
    text = """
- method: roll
  speed: 100
  heading: 0
  duration: 1
"""
    value = yaml.safe_load(text)
    assert value[0]["method"] == "roll"
