"""
Stage 2: Locale Detection

ЦКП: Определение локали (страна + язык) по тексту чека.

Входные данные: LayoutResult (строки текста)
Выходные данные: LocaleResult (код локали, уверенность)

Алгоритм:
1. Поиск ключевых слов локалей в тексте
2. Подсчёт совпадений для каждой локали
3. Выбор локали с максимальным счётом
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from loguru import logger

from .stage_1_layout import LayoutResult


# Ключевые слова для определения локалей
LOCALE_KEYWORDS: Dict[str, Set[str]] = {
    "de_DE": {
        # Суммы
        "summe", "gesamt", "gesamtbetrag", "zu zahlen", "bar", "gegeben", "ruckgeld",
        # Налоги
        "mwst", "ust", "steuer", "netto", "brutto",
        # Магазины
        "lidl", "aldi", "rewe", "edeka", "kaufland", "netto", "penny", "dm", "rossmann",
        # Валюта
        "eur", "euro",
        # Общие
        "danke", "vielen dank", "beleg", "kassenbon", "quittung",
        # Pfand
        "pfand", "leergut", "einweg", "mehrweg",
    },
    "pl_PL": {
        # Суммы
        "suma", "razem", "do zaplaty", "zaplacono", "gotowka", "reszta",
        # Налоги
        "ptu", "vat", "netto", "brutto", "stawka",
        # Магазины
        "biedronka", "lidl", "zabka", "żabka", "auchan", "carrefour", "tesco",
        # Валюта
        "pln", "zl", "zł",
        # Общие
        "dziekujemy", "paragon", "fiskalny",
    },
    "es_ES": {
        # Суммы
        "total", "importe", "efectivo", "cambio", "entregado",
        # Налоги
        "iva", "base", "cuota",
        # Магазины
        "mercadona", "carrefour", "lidl", "aldi", "dia", "eroski",
        # Валюта
        "eur", "euro",
        # Общие
        "gracias", "ticket", "factura",
    },
    "pt_PT": {
        # Суммы
        "total", "valor", "troco", "pago",
        # Налоги
        "iva", "taxa",
        # Магазины
        "continente", "pingo doce", "lidl", "aldi", "minipreco",
        # Валюта
        "eur", "euro",
        # Общие
        "obrigado", "talao", "recibo",
    },
    "cs_CZ": {
        # Суммы
        "celkem", "k uhrade", "hotove", "platba",
        # Налоги
        "dph",
        # Магазины
        "albert", "billa", "lidl", "kaufland", "tesco", "penny",
        # Валюта
        "kc", "czk", "korun",
        # Общие
        "dekujeme", "uctenka",
    },
    "bg_BG": {
        # Суммы
        "обща сума", "сума", "платено", "ресто",
        # Налоги
        "ддс",
        # Валюта
        "лв", "bgn", "лева",
        # Общие
        "благодарим", "касова бележка",
    },
    "uk_UA": {
        # Суммы
        "сума", "разом", "готівка", "здача",
        # Налоги
        "пдв",
        # Валюта
        "грн", "uah",
        # Общие
        "дякуємо", "чек", "фіскальний",
    },
    "tr_TR": {
        # Суммы
        "toplam", "nakit", "para ustu",
        # Налоги
        "kdv",
        # Валюта
        "tl", "try", "lira",
        # Общие
        "tesekkurler", "fis",
    },
    "th_TH": {
        # Суммы
        "รวม", "ทั้งหมด", "เงินสด", "ทอน",
        # Налоги
        "vat", "ภาษี",
        # Валюта
        "บาท", "thb",
        # Общие
        "ขอบคุณ", "ใบเสร็จ",
    },
    "en_IN": {
        # Суммы
        "total", "grand total", "cash", "change",
        # Налоги
        "gst", "cgst", "sgst", "tax",
        # Валюта
        "rs", "inr", "rupees",
        # Общие
        "thank you", "bill", "invoice",
    },
}

# Локаль по умолчанию
DEFAULT_LOCALE = "de_DE"
FALLBACK_LOCALE = "en_US"


@dataclass
class LocaleResult:
    """
    Результат Stage 2: Locale Detection.
    
    ЦКП: Определённая локаль с уверенностью.
    """
    locale_code: str                            # Код локали (de_DE, pl_PL, ...)
    confidence: float = 0.0                     # Уверенность (0.0 - 1.0)
    matched_keywords: List[str] = field(default_factory=list)  # Найденные ключевые слова
    scores: Dict[str, int] = field(default_factory=dict)       # Счёт по каждой локали
    
    def to_dict(self) -> dict:
        return {
            "locale_code": self.locale_code,
            "confidence": self.confidence,
            "matched_keywords": self.matched_keywords,
            "scores": self.scores,
        }


class LocaleStage:
    """
    Stage 2: Locale Detection.
    
    ЦКП: Определение локали по ключевым словам.
    """
    
    def __init__(
        self,
        locale_keywords: Optional[Dict[str, Set[str]]] = None,
        default_locale: str = DEFAULT_LOCALE,
    ):
        """
        Args:
            locale_keywords: Словарь {locale_code: {keywords}}
            default_locale: Локаль по умолчанию если не определена
        """
        self.locale_keywords = locale_keywords or LOCALE_KEYWORDS
        self.default_locale = default_locale
    
    def process(self, layout: LayoutResult) -> LocaleResult:
        """
        Определяет локаль по тексту чека.
        
        Args:
            layout: Результат Stage 1 (Layout)
            
        Returns:
            LocaleResult: Определённая локаль
        """
        logger.debug(f"[Stage 2: Locale] Анализ {len(layout.lines)} строк")
        
        # Объединяем весь текст в lowercase
        full_text = layout.full_text.lower()
        
        # Подсчитываем совпадения для каждой локали
        scores: Dict[str, int] = {}
        matched_by_locale: Dict[str, List[str]] = {}
        
        for locale_code, keywords in self.locale_keywords.items():
            score = 0
            matched = []
            
            for keyword in keywords:
                if keyword in full_text:
                    score += 1
                    matched.append(keyword)
            
            scores[locale_code] = score
            matched_by_locale[locale_code] = matched
        
        # Выбираем локаль с максимальным счётом
        if scores:
            best_locale = max(scores, key=scores.get)
            best_score = scores[best_locale]
            
            # Вычисляем уверенность
            total_possible = len(self.locale_keywords.get(best_locale, set()))
            confidence = best_score / total_possible if total_possible > 0 else 0.0
            
            # Если счёт слишком низкий, используем default
            if best_score < 2:
                logger.warning(f"[Stage 2: Locale] Низкий счёт ({best_score}), используем default: {self.default_locale}")
                best_locale = self.default_locale
                confidence = 0.0
                matched_by_locale[best_locale] = []
        else:
            best_locale = self.default_locale
            confidence = 0.0
            matched_by_locale[best_locale] = []
        
        result = LocaleResult(
            locale_code=best_locale,
            confidence=min(1.0, confidence),
            matched_keywords=matched_by_locale.get(best_locale, []),
            scores=scores,
        )
        
        logger.info(f"[Stage 2: Locale] Определена локаль: {best_locale} (confidence: {confidence:.2f})")
        
        return result
