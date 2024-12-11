import mss
import tempfile
import zlib
import struct

def screen_save() -> str:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        rgb_data = screenshot.rgb
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            write_png(temp_file.name, screenshot.width, screenshot.height, rgb_data)
            return temp_file.name

def write_png(filename, width, height, data):
    png_signature = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = create_png_chunk(b'IHDR', ihdr)
    raw_data = b''.join(b'\x00' + data[y * width * 3:(y + 1) * width * 3] for y in range(height))
    compressed_data = zlib.compress(raw_data, level=9)
    idat_chunk = create_png_chunk(b'IDAT', compressed_data)
    iend_chunk = create_png_chunk(b'IEND', b'')
    with open(filename, 'wb') as f:
        f.write(png_signature)
        f.write(ihdr_chunk)
        f.write(idat_chunk)
        f.write(iend_chunk)

def create_png_chunk(chunk_type, data):
    chunk_len = len(data)
    chunk_crc = zlib.crc32(chunk_type + data) & 0xffffffff
    return struct.pack("!I", chunk_len) + chunk_type + data + struct.pack("!I", chunk_crc)
