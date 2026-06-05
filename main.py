import sys
import os
import ctypes
import threading
import keyboard
import mss
import numpy as np
import argparse
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject, QRect

from overlay import OverlayWindow
from snipping_tool import SnippingWidget
from ocr_engine import OCREngine
from translator import TextTranslator

class TranslatorController(QObject):
    # Signal to update UI from background thread
    update_ui_signal = pyqtSignal(list)
    clear_ui_signal = pyqtSignal()
    start_snipping_signal = pyqtSignal()

    def __init__(self, ocr_langs=['ja', 'en'], deepl_lang='JA'):
        super().__init__()
        self.ocr = OCREngine(languages=ocr_langs)
        self.translator = TextTranslator(source_lang=deepl_lang, target_lang='VI')
        
        self.overlay = OverlayWindow()
        self.snipping = SnippingWidget()
        
        # Connect signals
        self.update_ui_signal.connect(self.overlay.update_translations)
        self.clear_ui_signal.connect(self.overlay.clear_overlay)
        self.start_snipping_signal.connect(self.snipping.start_snipping)
        self.snipping.on_selection_complete.connect(self.process_region)
        
        self.is_processing = False

    def toggle_action(self):
        if self.is_processing:
            print("Already processing, please wait...")
            return
            
        if self.overlay.translations:
            # Clear if already showing something
            self.clear_screen()
        else:
            # Start snipping if clear
            self.start_snipping_signal.emit()

    def process_region(self, rect: QRect):
        self.is_processing = True
        self.overlay.clear_overlay()
        print(f"Captured region: {rect.x()}, {rect.y()} - {rect.width()}x{rect.height()}")
        
        threading.Thread(target=self._process_region_worker, args=(rect,), daemon=True).start()

    def _process_region_worker(self, rect: QRect):
        try:
            # Fix deprecation warning by using MSS()
            with mss.MSS() as sct:
                # Capture the specific region
                monitor = {
                    "top": rect.y(), 
                    "left": rect.x(), 
                    "width": rect.width(), 
                    "height": rect.height()
                }
                sct_img = sct.grab(monitor)
                img_np = np.array(sct_img)
                # Drop Alpha channel and convert BGRA to RGB
                img_np = img_np[:, :, :3][:, :, ::-1]
            
            print("Running OCR on selected region...")
            results = self.ocr.extract_text(img_np)
            
            if not results:
                print("No text found in this region.")
                self.is_processing = False
                return
                
            # Combine all detected text in the selected region into one sentence
            # This fixes the issue where OCR splits a sentence across multiple lines
            original_text = "".join([res[1] for res in results])
            print(f"Extracted Text: {original_text}")
            
            # Translate the combined text
            translated_text = self.translator.translate(original_text)
            
            # Use the user's selected region as the only bounding box
            formatted_results = [{
                'rect': (rect.x(), rect.y(), rect.width(), rect.height()),
                'translated_text': translated_text
            }]
            
            print("Translation complete. Updating overlay...")
            self.update_ui_signal.emit(formatted_results)
            
        except Exception as e:
            print(f"Error processing region: {e}")
        finally:
            self.is_processing = False

    def toggle_full_screen_action(self):
        if self.is_processing:
            print("Already processing, please wait...")
            return
            
        if self.overlay.translations:
            # Clear if already showing something
            self.clear_screen()
        else:
            self.is_processing = True
            self.overlay.clear_overlay()
            print("Capturing full screen...")
            threading.Thread(target=self._process_full_screen_worker, daemon=True).start()

    def _process_full_screen_worker(self):
        try:
            with mss.MSS() as sct:
                # monitor 1 is the primary monitor
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                img_np = np.array(sct_img)
                # Drop Alpha channel and convert BGRA to RGB
                img_np = img_np[:, :, :3][:, :, ::-1]
            
            print("Running OCR on full screen with paragraph mode...")
            results = self.ocr.extract_text(img_np, paragraph=True)
            
            if not results:
                print("No text found on screen.")
                self.is_processing = False
                return
                
            formatted_results = self.ocr.format_results_for_overlay(results, paragraph=True)
            
            # Extract texts for batch translation
            original_texts = [item['original_text'] for item in formatted_results]
            print(f"Found {len(original_texts)} text boxes. Translating...")
            
            translated_texts = self.translator.translate_batch(original_texts)
            
            for i, item in enumerate(formatted_results):
                item['translated_text'] = translated_texts[i]
            
            print("Translation complete. Updating overlay...")
            self.update_ui_signal.emit(formatted_results)
            
        except Exception as e:
            print(f"Error processing full screen: {e}")
        finally:
            self.is_processing = False

    def clear_screen(self):
        print("Clearing overlay...")
        self.clear_ui_signal.emit()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    if not is_admin():
        print("Đang yêu cầu quyền Quản trị viên (Administrator)...")
        # Relaunch the script with admin rights
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{script}"'] + sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit()

    print("="*50)
    print("CHỌN NGÔN NGỮ NGUỒN (SOURCE LANGUAGE):")
    print("1. Tiếng Nhật (Mặc định)")
    print("2. Tiếng Hàn")
    print("3. Tiếng Trung")
    print("4. Tiếng Anh")
    print("5. Tiếng Đức")
    print("="*50)
    
    choice = input("Nhập lựa chọn của bạn (1/2/3/4/5) và nhấn Enter: ").strip()
    
    if choice == '2':
        ocr_langs = ['ko', 'en']
        deepl_lang = 'KO'
        lang_name = "Tiếng Hàn (ko)"
    elif choice == '3':
        # ch_sim for Simplified Chinese, ch_tra for Traditional
        ocr_langs = ['ch_sim', 'ch_tra', 'en']
        deepl_lang = 'ZH'
        lang_name = "Tiếng Trung (zh)"
    elif choice == '4':
        ocr_langs = ['en']
        deepl_lang = 'EN'
        lang_name = "Tiếng Anh (en)"
    elif choice == '5':
        ocr_langs = ['de', 'en']
        deepl_lang = 'DE'
        lang_name = "Tiếng Đức (de)"
    else:
        ocr_langs = ['ja', 'en']
        deepl_lang = 'JA'
        lang_name = "Tiếng Nhật (ja)"

    app = QApplication(sys.argv)
    
    # Initialize the controller
    controller = TranslatorController(ocr_langs=ocr_langs, deepl_lang=deepl_lang)
    
    # Register global hotkey
    keyboard.add_hotkey('f6', controller.toggle_action)
    keyboard.add_hotkey('f7', controller.toggle_full_screen_action)
    
    print("\n" + "="*50)
    print(f"Game Translator is running! (Ngôn ngữ nguồn: {lang_name})")
    print("Press F6 to select a region to translate.")
    print("Press F7 to scan and translate the full screen.")
    print("Press F6 or F7 again to clear the overlay.")
    print("Press Ctrl+C in this terminal to exit.")
    print("="*50 + "\n")
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
