import importlib
import os


def test_importlib():
    imported = importlib.import_module("os.path")
    assert imported is os.path

