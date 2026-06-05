import easyocr
import numpy as np

reader = easyocr.Reader(['ja', 'en'], gpu=False)
# Create a dummy image
img = np.zeros((100, 100, 3), dtype=np.uint8)
res = reader.readtext(img, paragraph=True)
print("Paragraph=True results:")
print(res)

res2 = reader.readtext(img, paragraph=False)
print("Paragraph=False results:")
print(res2)
