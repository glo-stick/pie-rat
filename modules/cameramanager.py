'''This code will be precompiled, I put this here incase you don't trust, or the hosting provider deletes the precompiled one'''


import cv2
import sys
import tempfile
import os

def list_cameras():
    """
    List all available cameras.
    :return: List of camera indices.
    """
    available_cameras = []
    for index in range(10):  # Check the first 10 camera indices
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            available_cameras.append(index)
            cap.release()
    return available_cameras

def capture_image(camera_index=0):
    """
    Capture an image from the specified camera and save it as a temporary file.
    :param camera_index: Index of the camera to use.
    :return: Path to the saved image or an error message.
    """
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return f'Error: Could not open camera {camera_index}.'
        
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return 'Error: Failed to capture image.'
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        cv2.imwrite(temp_file.name, frame)
        return temp_file.name
    
    except Exception as e:
        return f'Error capturing image: {e}'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: cameramanager.py <command> [args...]')
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'list':
        cameras = list_cameras()
        if cameras:
            print('\n'.join(map(str, cameras)))
        else:
            print('No cameras detected.')
    elif command == 'capture':
        camera_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        result = capture_image(camera_index)
        print(result)
    else:
        print('Unknown command.')
