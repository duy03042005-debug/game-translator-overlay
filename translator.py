import deepl
from deep_translator import GoogleTranslator

class TextTranslator:
    def __init__(self, source_lang='JA', target_lang='VI', engine='deepl'):
        """
        Initialize the Translator (DeepL or Google).
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.engine = engine
        
        if self.engine == 'deepl':
            self.auth_key = "fa011ab4-8464-46ed-b862-4054748bba32:fx"
            self.translator = deepl.Translator(self.auth_key)
        elif self.engine == 'google':
            # Map languages for Google Translator
            src = self.source_lang.lower().replace('-us', '').replace('zh', 'zh-CN')
            tgt = self.target_lang.lower().replace('-us', '').replace('zh', 'zh-CN')
            self.translator = GoogleTranslator(source=src, target=tgt)

    def translate(self, text):
        """
        Translate a single text string.
        """
        if not text or text.isspace():
            return ""
            
        try:
            if self.engine == 'deepl':
                result = self.translator.translate_text(text, source_lang=self.source_lang, target_lang=self.target_lang)
                return result.text
            elif self.engine == 'google':
                return self.translator.translate(text)
        except Exception as e:
            print(f"{self.engine.capitalize()} Translation error: {e}")
            return text

    def translate_batch(self, texts):
        """
        Translate a list of text strings.
        """
        if not texts:
            return []
            
        try:
            if self.engine == 'deepl':
                results = self.translator.translate_text(texts, source_lang=self.source_lang, target_lang=self.target_lang)
                return [result.text for result in results]
            elif self.engine == 'google':
                return self.translator.translate_batch(texts)
        except Exception as e:
            print(f"{self.engine.capitalize()} Batch translation error: {e}")
            # Fallback to returning original text if translation fails completely
            return texts
