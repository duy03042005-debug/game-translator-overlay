import deepl

class TextTranslator:
    def __init__(self, source_lang='JA', target_lang='VI'):
        """
        Initialize the DeepL Translator.
        Defaults to Japanese (JA) -> Vietnamese (VI).
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        # Use the provided DeepL API Key
        self.auth_key = "fa011ab4-8464-46ed-b862-4054748bba32:fx"
        self.translator = deepl.Translator(self.auth_key)

    def translate(self, text):
        """
        Translate a single text string.
        """
        if not text or text.isspace():
            return ""
            
        try:
            result = self.translator.translate_text(text, source_lang=self.source_lang, target_lang=self.target_lang)
            return result.text
        except Exception as e:
            print(f"DeepL Translation error: {e}")
            return text

    def translate_batch(self, texts):
        """
        Translate a list of text strings.
        """
        if not texts:
            return []
            
        try:
            # DeepL can accept a list of strings and translates them in batch
            results = self.translator.translate_text(texts, source_lang=self.source_lang, target_lang=self.target_lang)
            return [result.text for result in results]
        except Exception as e:
            print(f"DeepL Batch translation error: {e}")
            # Fallback to returning original text if translation fails completely
            return texts
