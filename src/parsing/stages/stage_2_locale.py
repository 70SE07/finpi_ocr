"""
Stage 2: Locale Detection (Stable Version)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from .stage_1_layout import LayoutResult
from ..locales.config_loader import ConfigLoader, LocaleConfig


@dataclass
class LocaleResult:
    locale_code: str
    confidence: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    scores: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "locale_code": self.locale_code,
            "confidence": self.confidence,
            "matched_keywords": self.matched_keywords,
            "scores": self.scores,
        }


class LocaleStage:
    def __init__(self, config_loader: Optional[ConfigLoader] = None, default_locale: str = "de_DE"):
        self.config_loader = config_loader or ConfigLoader()
        self.default_locale = default_locale
        self._cached_keywords: Optional[Dict[str, List[str]]] = None
    
    def _get_all_locale_keywords(self) -> Dict[str, List[str]]:
        if self._cached_keywords is not None:
            return self._cached_keywords
            
        keywords_map = {}
        locales_dir = Path(__file__).parent.parent / "locales"
        available_locales = [d.name for d in locales_dir.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
        
        for locale_code in available_locales:
            try:
                config = self.config_loader.load(locale_code)
                if config.detection_keywords:
                    keywords_map[locale_code] = config.detection_keywords
            except: continue
                
        self._cached_keywords = keywords_map
        return keywords_map

    def process(self, layout: LayoutResult) -> LocaleResult:
        logger.debug(f"[Stage 2: Locale] Динамический анализ {len(layout.lines)} строк")
        
        full_text = layout.full_text.lower()
        locale_keywords = self._get_all_locale_keywords()
        
        scores: Dict[str, int] = {}
        matched_by_locale: Dict[str, List[str]] = {}
        
        for locale_code, keywords in locale_keywords.items():
            score = 0
            matched = []
            for kw in keywords:
                # Ищем слово с границами или специфические коды типа "PT"
                if kw.lower() in full_text:
                    score += 1
                    matched.append(kw)
            
            scores[locale_code] = score
            matched_by_locale[locale_code] = matched
            
        if not any(scores.values()):
            logger.warning(f"[Stage 2: Locale] Ключевые слова не найдены, используем {self.default_locale}")
            return LocaleResult(locale_code=self.default_locale)
            
        # Выбираем лучшую локаль. При равенстве очков берем ту, где совпадений БОЛЬШЕ (если есть приоритеты)
        # Или ту, у которой совпавшие слова более "длинные" (уникальные)
        best_locale = max(scores, key=lambda l: (scores[l], sum(len(w) for w in matched_by_locale[l])))
        best_score = scores[best_locale]
        
        total_possible = len(locale_keywords.get(best_locale, []))
        confidence = best_score / total_possible if total_possible > 0 else 0.0
        
        if best_score < 2:
            best_locale = self.default_locale
            confidence = 0.0
            
        logger.info(f"[Stage 2: Locale] Определена локаль: {best_locale} (score: {best_score})")
        
        return LocaleResult(
            locale_code=best_locale,
            confidence=confidence,
            matched_keywords=matched_by_locale.get(best_locale, []),
            scores=scores
        )
