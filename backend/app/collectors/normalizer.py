import re
import hashlib

class Normalizer:
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizes whitespace and removes redundant empty lines to produce clean text.
        """
        if not text:
            return ""
        # Replace multiple spaces with a single space
        normalized = re.sub(r'\s+', ' ', text)
        return normalized.strip()

    @staticmethod
    def generate_hash(content: str) -> str:
        """
        Generates a SHA-256 hash of the normalized content.
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

