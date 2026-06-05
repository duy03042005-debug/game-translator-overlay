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

    def __init__(self, ocr_langs=['ja', 'en'], deepl_lang='JA', lang_name='Tiếng Nhật (ja)', target_lang='VI', target_lang_name='Tiếng Việt (vi)', engine='deepl', engine_name='DeepL'):
        super().__init__()
        self.ocr_langs = ocr_langs
        self.deepl_lang = deepl_lang
        self.target_lang = target_lang
        self.engine = engine
        
        self.ocr = OCREngine(languages=ocr_langs)
        self.translator = TextTranslator(source_lang=deepl_lang, target_lang=target_lang, engine=engine)
        self.lang_name = lang_name
        self.target_lang_name = target_lang_name
        self.engine_name = engine_name
        
        self.last_rect = None
        self.is_changing_lang = False
        
        self.hotkeys = {
            'region': 'f6',
            'fullscreen': 'f7',
            'retranslate': 'f8',
            'language': 'f9',
            'target_language': 'f11',
            'engine': 'f12',
            'change_keys': 'f10'
        }
        self.hook_handles = {}
        
        self.overlay = OverlayWindow()
        self.snipping = SnippingWidget()
        
        # Connect signals
        self.update_ui_signal.connect(self.overlay.update_translations)
        self.clear_ui_signal.connect(self.overlay.clear_overlay)
        self.start_snipping_signal.connect(self.snipping.start_snipping)
        self.snipping.on_selection_complete.connect(self.process_region)
        
        self.is_processing = False

    def print_menu(self):
        print("\n" + "="*50)
        print(f"Game Translator is running! (Nguồn: {self.lang_name} -> Đích: {self.target_lang_name} | Engine: {self.engine_name})")
        print("DANH SÁCH PHÍM TẮT:")
        print(f"[{self.hotkeys['region'].upper()}] - Chọn vùng dịch")
        print(f"[{self.hotkeys['fullscreen'].upper()}] - Dịch toàn màn hình")
        print(f"[{self.hotkeys['retranslate'].upper()}] - Dịch lại vùng vừa chọn")
        print(f"[{self.hotkeys['language'].upper()}] - Đổi ngôn ngữ NGUỒN")
        print(f"[{self.hotkeys['target_language'].upper()}] - Đổi ngôn ngữ ĐÍCH")
        print(f"[{self.hotkeys['engine'].upper()}] - Đổi bộ máy dịch (Engine)")
        print(f"[{self.hotkeys['change_keys'].upper()}] - Đổi phím tắt")
        print("Bấm lại phím dịch bất kỳ để xóa bản dịch trên màn hình.")
        print("Bấm Ctrl+C trong terminal này để thoát.")
        print("="*50 + "\n")

    def register_hotkeys(self):
        for name, handle in self.hook_handles.items():
            try:
                keyboard.remove_hotkey(handle)
            except:
                pass
        self.hook_handles.clear()
        
        self.hook_handles['region'] = keyboard.add_hotkey(self.hotkeys['region'], self.toggle_action)
        self.hook_handles['fullscreen'] = keyboard.add_hotkey(self.hotkeys['fullscreen'], self.toggle_full_screen_action)
        self.hook_handles['retranslate'] = keyboard.add_hotkey(self.hotkeys['retranslate'], self.translate_last_region_action)
        self.hook_handles['language'] = keyboard.add_hotkey(self.hotkeys['language'], self.change_language_action)
        self.hook_handles['target_language'] = keyboard.add_hotkey(self.hotkeys['target_language'], self.change_target_language_action)
        self.hook_handles['engine'] = keyboard.add_hotkey(self.hotkeys['engine'], self.change_engine_action)
        self.hook_handles['change_keys'] = keyboard.add_hotkey(self.hotkeys['change_keys'], self.change_hotkeys_action)
        
        self.print_menu()

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
        self.last_rect = rect
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

    def translate_last_region_action(self):
        if self.is_processing:
            print("Already processing, please wait...")
            return
            
        if not self.last_rect:
            print("Chưa có vùng nào được chọn trước đó. Vui lòng bấm F6 để chọn vùng lần đầu.")
            return

        if self.overlay.translations:
            self.clear_screen()
        else:
            self.is_processing = True
            self.overlay.clear_overlay()
            print("Dịch lại vùng đã chọn trước đó...")
            threading.Thread(target=self._process_region_worker, args=(self.last_rect,), daemon=True).start()

    def change_language_action(self):
        if self.is_processing or self.is_changing_lang:
            print("Hệ thống đang bận, vui lòng đợi...")
            return
            
        self.is_changing_lang = True
        try:
            print("\n" + "="*50)
            print("CHỌN LẠI NGÔN NGỮ NGUỒN (SOURCE LANGUAGE):")
            print("1. Tiếng Nhật")
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
                
            self.lang_name = lang_name
            print(f"Đang đổi ngôn ngữ NGUỒN sang {lang_name}...")
            self.ocr_langs = ocr_langs
            self.deepl_lang = deepl_lang
            self.ocr = OCREngine(languages=ocr_langs)
            self.translator = TextTranslator(source_lang=deepl_lang, target_lang=self.target_lang, engine=self.engine)
            print(f"Đã đổi thành công sang {lang_name}!")
        except Exception as e:
            print(f"Lỗi khi đổi ngôn ngữ nguồn: {e}")
        finally:
            self.is_changing_lang = False

    def change_target_language_action(self):
        if self.is_processing or self.is_changing_lang:
            print("Hệ thống đang bận, vui lòng đợi...")
            return
            
        self.is_changing_lang = True
        try:
            print("\n" + "="*50)
            print("CHỌN NGÔN NGỮ ĐÍCH (TARGET LANGUAGE):")
            print("1. Tiếng Việt (Mặc định)")
            print("2. Tiếng Anh")
            print("3. Tiếng Nhật")
            print("4. Tiếng Đức")
            print("="*50)
            
            choice = input("Nhập lựa chọn của bạn (1/2/3/4) và nhấn Enter: ").strip()
            
            if choice == '2':
                target_lang = 'EN-US'
                lang_name = "Tiếng Anh (en)"
            elif choice == '3':
                target_lang = 'JA'
                lang_name = "Tiếng Nhật (ja)"
            elif choice == '4':
                target_lang = 'DE'
                lang_name = "Tiếng Đức (de)"
            else:
                target_lang = 'VI'
                lang_name = "Tiếng Việt (vi)"
                
            self.target_lang = target_lang
            self.target_lang_name = lang_name
            print(f"Đang đổi ngôn ngữ ĐÍCH sang {lang_name}...")
            # We don't need to recreate OCR, only Translator
            self.translator = TextTranslator(source_lang=self.deepl_lang, target_lang=target_lang, engine=self.engine)
            print(f"Đã đổi thành công sang {lang_name}!")
        except Exception as e:
            print(f"Lỗi khi đổi ngôn ngữ đích: {e}")
        finally:
            self.is_changing_lang = False

    def change_engine_action(self):
        if self.is_processing or self.is_changing_lang:
            print("Hệ thống đang bận, vui lòng đợi...")
            return
            
        self.is_changing_lang = True
        try:
            print("\n" + "="*50)
            print("CHỌN BỘ MÁY DỊCH (TRANSLATION ENGINE):")
            print("1. DeepL (Mặc định - Dịch hay hơn nhưng có giới hạn API)")
            print("2. Google Translate (Miễn phí, không giới hạn)")
            print("="*50)
            
            choice = input("Nhập lựa chọn của bạn (1/2) và nhấn Enter: ").strip()
            
            if choice == '2':
                self.engine = 'google'
                self.engine_name = 'Google Translate'
            else:
                self.engine = 'deepl'
                self.engine_name = 'DeepL'
                
            print(f"Đang đổi bộ máy dịch sang {self.engine_name}...")
            self.translator = TextTranslator(source_lang=self.deepl_lang, target_lang=self.target_lang, engine=self.engine)
            print(f"Đã đổi thành công sang {self.engine_name}!")
        except Exception as e:
            print(f"Lỗi khi đổi bộ máy dịch: {e}")
        finally:
            self.is_changing_lang = False

    def change_hotkeys_action(self):
        if self.is_processing or self.is_changing_lang:
            print("Hệ thống đang bận, vui lòng đợi...")
            return
            
        self.is_changing_lang = True
        try:
            print("\n" + "="*50)
            print("CÀI ĐẶT PHÍM TẮT:")
            print("Nhập phím bạn muốn gán (VD: f1, f2, shift+a...). Nhấn Enter để giữ nguyên phím cũ.")
            
            new_region = input(f"Phím [Chọn vùng dịch] (hiện tại: {self.hotkeys['region']}): ").strip().lower()
            if new_region: self.hotkeys['region'] = new_region
            
            new_fs = input(f"Phím [Dịch toàn màn hình] (hiện tại: {self.hotkeys['fullscreen']}): ").strip().lower()
            if new_fs: self.hotkeys['fullscreen'] = new_fs
            
            new_re = input(f"Phím [Dịch lại vùng vừa chọn] (hiện tại: {self.hotkeys['retranslate']}): ").strip().lower()
            if new_re: self.hotkeys['retranslate'] = new_re
            
            new_lang = input(f"Phím [Đổi ngôn ngữ nguồn] (hiện tại: {self.hotkeys['language']}): ").strip().lower()
            if new_lang: self.hotkeys['language'] = new_lang

            new_target = input(f"Phím [Đổi ngôn ngữ đích] (hiện tại: {self.hotkeys['target_language']}): ").strip().lower()
            if new_target: self.hotkeys['target_language'] = new_target

            new_engine = input(f"Phím [Đổi bộ máy dịch] (hiện tại: {self.hotkeys['engine']}): ").strip().lower()
            if new_engine: self.hotkeys['engine'] = new_engine

            new_change = input(f"Phím [Đổi phím tắt] (hiện tại: {self.hotkeys['change_keys']}): ").strip().lower()
            if new_change: self.hotkeys['change_keys'] = new_change
            
            print("Đang cập nhật phím tắt...")
            self.register_hotkeys()
        except Exception as e:
            print(f"Lỗi khi đổi phím tắt: {e}")
        finally:
            self.is_changing_lang = False

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
    controller = TranslatorController(ocr_langs=ocr_langs, deepl_lang=deepl_lang, lang_name=lang_name)
    controller.register_hotkeys()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
