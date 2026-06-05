import easyocr
import numpy as np

class OCREngine:
    def __init__(self, languages=['ja', 'en']):
        """
        Initialize the EasyOCR reader. 
        Note: This will download the models on the first run if they are not already downloaded.
        """
        print(f"Initializing OCR with languages: {languages}...")
        # gpu=True will use CUDA if available, otherwise falls back to CPU
        self.reader = easyocr.Reader(languages, gpu=True)
        print("OCR Initialized.")

    def extract_text(self, image_np, paragraph=False):
        """
        Extract text from a numpy array image.
        Returns a list of tuples: (bounding_box, text, confidence) if paragraph=False
        Or (bounding_box, text) if paragraph=True
        bounding_box format: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        """
        # Read text from the numpy image (RGB format is preferred by easyocr)
        results = self.reader.readtext(image_np, paragraph=paragraph)
        return results

    def format_results_for_overlay(self, ocr_results, paragraph=False):
        """
        Converts the raw OCR results into a format easier to use by our overlay.
        Calculates bounding box rects (x, y, w, h).
        """
        formatted = []
        if paragraph:
            for bbox, text in ocr_results:
                top_left = bbox[0]
                bottom_right = bbox[2]
                
                x = int(min(top_left[0], bbox[3][0]))
                y = int(min(top_left[1], bbox[1][1]))
                
                max_x = int(max(bottom_right[0], bbox[1][0]))
                max_y = int(max(bottom_right[1], bbox[3][1]))
                
                w = max_x - x
                h = max_y - y
                
                formatted.append({
                    'rect': (x, y, w, h),
                    'original_text': text,
                    'confidence': 1.0
                })
        else:
            for bbox, text, conf in ocr_results:
                if conf < 0.2:  # Skip very low confidence detections
                    continue
                    
                # bbox is [[top_left], [top_right], [bottom_right], [bottom_left]]
                top_left = bbox[0]
                bottom_right = bbox[2]
                
                x = int(min(top_left[0], bbox[3][0]))
                y = int(min(top_left[1], bbox[1][1]))
                
                max_x = int(max(bottom_right[0], bbox[1][0]))
                max_y = int(max(bottom_right[1], bbox[3][1]))
                
                w = max_x - x
                h = max_y - y
                
                formatted.append({
                    'rect': (x, y, w, h),
                    'original_text': text,
                    'confidence': conf
                })
                
        return formatted
