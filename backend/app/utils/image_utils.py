from pathlib import Path
from PIL import Image
import cv2
import numpy as np

def resize_image(image_path: Path, max_width: int = 1920, max_height: int = 1920) -> Image.Image:
    """Resize image while maintaining aspect ratio."""
    image = Image.open(image_path)
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    return image

def crop_image(image: Image.Image, x: int, y: int, w: int, h: int) -> Image.Image:
    """Crop image to bubble region."""
    return image.crop((x, y, x + w, y + h))

def detect_text_region(image_array: np.ndarray) -> np.ndarray:
    """Detect text pixels in image using threshold."""
    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    return thresh

def apply_gaussian_blur(image_array: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """Apply Gaussian blur to smooth image."""
    return cv2.GaussianBlur(image_array, (kernel_size, kernel_size), 0)
