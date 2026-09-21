import os
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app.py"))

def test_app_initialization():
    at = AppTest.from_file(APP_PATH).run()
    assert not at.exception
    assert at.title[0].value == "🎬 MiniMax H3 影片批次高清化 Web 原型系統"

def test_invalid_folder_path():
    at = AppTest.from_file(APP_PATH).run()
    
    at.text_input[0].set_value("non_existent_folder_path").run()
    
    assert "不存在" in at.warning[0].value
