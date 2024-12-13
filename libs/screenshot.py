import tempfile
from PIL import ImageGrab

def screen_save() -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            screenshot = ImageGrab.grab()
            screenshot.save(temp_file.name)
            return temp_file.name
    except Exception as e:
        raise RuntimeError(f"Failed to capture screenshot: {str(e)}")
