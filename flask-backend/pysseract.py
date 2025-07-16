import pytesseract

# Expose image_to_string to mimic pysseract API

# Optionally, allow configuration of tesseract_cmd
if hasattr(pytesseract, 'pytesseract'):
    tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
else:
    tesseract_cmd = getattr(pytesseract, 'tesseract_cmd', None)

image_to_string = pytesseract.image_to_string

