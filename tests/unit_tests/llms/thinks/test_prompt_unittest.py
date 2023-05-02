from ghoshell.llms.thinks.prompt_unittest import PromptUnitTestLoader


def test_prompt_unittest_storage_1():
    content = """
# DESC
desc

# PROMPT
- a
- b

# CONCLUSION
* hello world

# EXPECT 
nothing
"""

    config = PromptUnitTestLoader.load_test_case(content)
    assert config.desc == "desc"
    assert config.prompt == "- a\n- b"
    assert config.conclusion == "* hello world"
    assert config.expect == "nothing"


def test_prompt_unittest_storage_2():
    content = """
# DESC
# PROMPT

# CONCLUSION

abc
efg
"""

    config = PromptUnitTestLoader.load_test_case(content)
    assert config.desc == ""
    assert config.prompt == ""
    assert config.conclusion == "abc\nefg"
    assert config.expect == ""


def test_prompt_unittest_storage_3():
    content = """
# DESC
a

# PROMPT

wahahaha~
# CONCLUSION

abc
efg

# DESC
b
"""

    config = PromptUnitTestLoader.load_test_case(content)
    assert config.desc == "b"
    assert config.prompt == "wahahaha~"
    assert config.conclusion == "abc\nefg"
    assert config.expect == ""
