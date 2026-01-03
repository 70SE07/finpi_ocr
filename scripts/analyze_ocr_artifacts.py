"""
Анализатор OCR-артефактов

Сравнивает raw_ocr результат с ground_truth и выявляет различия.
Используется для ручной валидации и документирования артефактов.

Использование:
    python scripts/analyze_ocr_artifacts.py <receipt_id>

Пример:
    python scripts/analyze_ocr_artifacts.py IMG_1292
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher

# Путь к проекту
PROJECT_ROOT = Path("/Users/sergejevsukov/Downloads/Finpi_OCR")


class ArtifactAnalyzer:
    """Анализирует OCR артефакты сравнивая с Ground Truth."""

    def __init__(self, receipt_id: str):
        self.receipt_id = receipt_id
        self.artifacts = []
        self.metadata = {}

    def load_data(self) -> Tuple[Optional[dict], Optional[dict]]:
        """Загружает raw_ocr и ground_truth данные."""
        # Поиск raw_ocr.json
        raw_ocr_paths = list(PROJECT_ROOT.glob(f"data/output/{self.receipt_id}*/raw_ocr.json"))
        if not raw_ocr_paths:
            print(f"❌ raw_ocr.json не найден для {self.receipt_id}")
            return None, None

        raw_ocr_path = raw_ocr_paths[0]
        with open(raw_ocr_path, 'r', encoding='utf-8') as f:
            raw_ocr = json.load(f)

        # Поиск ground_truth
        gt_paths = list(PROJECT_ROOT.glob(f"docs/ground_truth/*{self.receipt_id}*.json"))
        if not gt_paths:
            print(f"⚠️  ground_truth не найден для {self.receipt_id}")
            return raw_ocr, None

        gt_path = gt_paths[0]
        with open(gt_path, 'r', encoding='utf-8') as f:
            gt_data = json.load(f)

        return raw_ocr, gt_data

    def extract_metadata(self, raw_ocr: dict, gt_data: dict):
        """Извлекает метаданные из чека."""
        locale = gt_data.get("locale", "unknown")
        store = gt_data.get("store", {}).get("brand", "unknown")
        source_file = raw_ocr.get("metadata", {}).get("source_file", self.receipt_id)

        self.metadata = {
            "locale": locale,
            "store": store,
            "source_file": source_file,
            "total_words": len(raw_ocr.get("words", [])),
            "total_items": len(gt_data.get("items", []))
        }

    def fuzzy_find_in_text(self, target: str, text: str, threshold: float = 0.6) -> Tuple[bool, str, float]:
        """
        Ищет target в text с нечётким совпадением.

        Returns:
            (found, matched_text, similarity)
        """
        target_clean = self.clean_text(target)
        text_clean = self.clean_text(text)

        if target_clean in text_clean:
            return True, target_clean, 1.0

        # Проверяем подстроки
        words_in_text = text_clean.split()
        for word in words_in_text:
            similarity = SequenceMatcher(None, target_clean.lower(), word.lower()).ratio()
            if similarity >= threshold:
                return True, word, similarity

        return False, "", 0.0

    def clean_text(self, text: str) -> str:
        """Очищает текст для сравнения."""
        return re.sub(r'[\s\-\*\'"„"]+', '', text).lower()

    def analyze_item_names(self, raw_ocr: dict, gt_data: dict):
        """Анализирует названия товаров."""
        ocr_text = raw_ocr.get("full_text", "")
        gt_items = gt_data.get("items", [])

        for item in gt_items:
            name = item.get("raw_name", item.get("name", ""))

            # Ищем в OCR
            found, matched, similarity = self.fuzzy_find_in_text(name, ocr_text)

            if not found:
                # Слово не найдено - WORD_SPLIT или CHAR_MISS
                self.artifacts.append({
                    "type": "WORD_SPLIT",
                    "ocr_text": "NOT FOUND",
                    "expected_text": name,
                    "context": name,
                    "suggestion": "Проверить разрыв слова или потерю символов"
                })
            elif similarity < 1.0:
                # Найдено с отличиями
                differences = self.find_differences(name, matched)
                for diff in differences:
                    self.artifacts.append({
                        "type": diff["type"],
                        "ocr_text": matched,
                        "expected_text": name,
                        "context": matched,
                        "suggestion": diff["suggestion"]
                    })

    def find_differences(self, expected: str, actual: str) -> List[Dict]:
        """Находит типы различий между строками."""
        differences = []

        # Проверка на похожие символы
        char_pairs = [
            ("0", "O"), ("1", "l"), ("l", "1"), ("5", "S"), ("S", "5")
        ]
        for ocr_char, exp_char in char_pairs:
            if ocr_char in actual and exp_char in expected:
                # Сравниваем позиции
                for i, (a, e) in enumerate(zip(actual, expected)):
                    if a == ocr_char and e == exp_char:
                        differences.append({
                            "type": "CHAR_SUB",
                            "suggestion": f"{ocr_char} → {exp_char} на позиции {i}"
                        })
                        break

        # Проверка длины
        if len(actual) != len(expected):
            if len(actual) < len(expected):
                differences.append({
                    "type": "CHAR_MISS",
                    "suggestion": f"Пропуск символов: ожидаем {len(expected)} chars, найдено {len(actual)}"
                })
            else:
                differences.append({
                    "type": "CHAR_EXTRA",
                    "suggestion": f"Лишние символы: ожидаем {len(expected)} chars, найдено {len(actual)}"
                })

        # Если различия не нашли типизированными правилами
        if not differences:
            differences.append({
                "type": "UNKNOWN",
                "suggestion": "Требуется ручной анализ"
            })

        return differences

    def analyze_prices(self, raw_ocr: dict, gt_data: dict):
        """Анализирует цены."""
        ocr_text = raw_ocr.get("full_text", "")
        gt_items = gt_data.get("items", [])

        for item in gt_items:
            price = item.get("total_price")
            if price is None:
                continue

            # Формируем паттерн цены
            price_str = f"{price:.2f}"
            price_alt = price_str.replace(".", ",")

            # Проверяем наличие в тексте
            if price_str not in ocr_text and price_alt not in ocr_text:
                # Цена не найдена - возможно NUM_FMT
                self.artifacts.append({
                    "type": "NUM_FMT",
                    "ocr_text": "NOT FOUND",
                    "expected_text": price_str,
                    "context": f"Товар: {item.get('raw_name', '?')}",
                    "suggestion": "Проверить формат разделителя (запятая/точка)"
                })

    def analyze_garbage(self, raw_ocr: dict):
        """Ищет мусорные символы."""
        text = raw_ocr.get("full_text", "")

        # Паттерны мусора
        garbage_patterns = [
            (r'[*]{3,}', "***", "Множественные звёздочки"),
            (r'[-]{3,}', "---", "Линии из дефисов"),
            (r'\|{2,}', "|||", "Вертикальные линии"),
            (r'~{3,}', "~~~", "Тильды"),
            (r'[*]{2}[@][*]{2}', "**@**", "Маскированные символы"),
            (r'[*]{4}[*]{4}', "****", "Маскированные символы"),
        ]

        for pattern, example, desc in garbage_patterns:
            if re.search(pattern, text):
                # Ищем все вхождения
                matches = re.findall(pattern, text)
                for match in matches[:3]:  # Максимум 3 примера
                    self.artifacts.append({
                        "type": "GARBAGE",
                        "ocr_text": match,
                        "expected_text": "",
                        "context": text[max(0, text.find(match)-20):text.find(match)+20],
                        "suggestion": f"Удалить: {desc}"
                    })

    def analyze_diacritics(self, locale: str, raw_ocr: dict, gt_data: dict):
        """Анализирует потерю диакритики."""
        diacritics_by_locale = {
            "pl_PL": "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
            "cs_CZ": "áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ",
            "de_DE": "äöüßÄÖÜ",
            "es_ES": "áéíóúüñçÁÉÍÓÚÜÑÇ",
        }

        diacritics = diacritics_by_locale.get(locale)
        if not diacritics:
            return

        ocr_text = raw_ocr.get("full_text", "")
        gt_items = gt_data.get("items", [])

        for item in gt_items:
            name = item.get("raw_name", item.get("name", ""))
            if not any(d in name for d in diacritics):
                continue

            # Проверяем есть ли диакритика в OCR
            found, matched, _ = self.fuzzy_find_in_text(name, ocr_text, threshold=0.8)

            if found:
                # Сравниваем наличие диакритики
                for d in diacritics:
                    if d in name and d not in matched:
                        self.artifacts.append({
                            "type": "DIAC_LOSS",
                            "ocr_text": matched,
                            "expected_text": name,
                            "context": name,
                            "suggestion": f"Потеря диакритики: {d}"
                        })

    def analyze_script_mix(self, locale: str, raw_ocr: dict, gt_data: dict):
        """Анализирует смешение алфавитов (кириллица/латиница)."""
        if locale not in ["uk_UA", "bg_BG", "ru_RU"]:
            return

        # Пары похожих символов
        script_pairs = [
            ("a", "а"), ("e", "е"), ("o", "о"), ("p", "р"),
            ("c", "с"), ("x", "х"), ("i", "і"), ("y", "у"),
            ("B", "В"), ("M", "М"), ("H", "Н"), ("P", "Р"),
            ("T", "Т"), ("K", "К")
        ]

        ocr_text = raw_ocr.get("full_text", "")
        gt_items = gt_data.get("items", [])

        for item in gt_items:
            name = item.get("raw_name", item.get("name", ""))

            # Ищем в OCR
            found, matched, _ = self.fuzzy_find_in_text(name, ocr_text, threshold=0.7)

            if found:
                for latin, cyrillic in script_pairs:
                    if latin in matched and cyrillic in name:
                        self.artifacts.append({
                            "type": "SCRIPT_MIX",
                            "ocr_text": matched,
                            "expected_text": name,
                            "context": matched,
                            "suggestion": f"Замена латинской {latin} на кириллическую {cyrillic}"
                        })
                    elif cyrillic in matched and latin in name:
                        self.artifacts.append({
                            "type": "SCRIPT_MIX",
                            "ocr_text": matched,
                            "expected_text": name,
                            "context": matched,
                            "suggestion": f"Замена кириллической {cyrillic} на латинскую {latin}"
                        })

    def analyze(self) -> dict:
        """Выполняет полный анализ чека."""
        print(f"\n{'='*60}")
        print(f"Анализ чека: {self.receipt_id}")
        print(f"{'='*60}\n")

        # Загрузка данных
        raw_ocr, gt_data = self.load_data()
        if not raw_ocr:
            return {"error": "raw_ocr not found"}
        if not gt_data:
            print("⚠️  Ground Truth не найден, анализирую без эталона\n")
            self.analyze_garbage(raw_ocr)
            return self._format_result()

        # Метаданные
        self.extract_metadata(raw_ocr, gt_data)
        print(f"Локаль: {self.metadata['locale']}")
        print(f"Магазин: {self.metadata['store']}")
        print(f"Слов в OCR: {self.metadata['total_words']}")
        print(f"Товаров в GT: {self.metadata['total_items']}\n")

        # Анализ
        self.analyze_item_names(raw_ocr, gt_data)
        self.analyze_prices(raw_ocr, gt_data)
        self.analyze_garbage(raw_ocr)
        self.analyze_diacritics(self.metadata['locale'], raw_ocr, gt_data)
        self.analyze_script_mix(self.metadata['locale'], raw_ocr, gt_data)

        return self._format_result()

    def _format_result(self) -> dict:
        """Форматирует результат в структурированный вид."""
        # Группировка по типам
        by_type = {}
        for artifact in self.artifacts:
            art_type = artifact["type"]
            if art_type not in by_type:
                by_type[art_type] = []
            by_type[art_type].append(artifact)

        return {
            "id": f"{self.metadata.get('locale', 'unknown')}_{self.receipt_id}",
            "receipt_id": self.receipt_id,
            "locale": self.metadata.get("locale", "unknown"),
            "store": self.metadata.get("store", "unknown"),
            "source_file": self.metadata.get("source_file", self.receipt_id),
            "artifacts": self.artifacts,
            "statistics": {
                "total_words": self.metadata.get("total_words", 0),
                "artifacts_found": len(self.artifacts),
                "by_type": {k: len(v) for k, v in by_type.items()}
            }
        }

    def print_summary(self):
        """Выводит краткую сводку."""
        if not self.artifacts:
            print("✅ Артефакты не найдены")
            return

        by_type = {}
        for a in self.artifacts:
            by_type[a["type"]] = by_type.get(a["type"], 0) + 1

        print(f"\nНайдено артефактов: {len(self.artifacts)}")
        print("По типам:")
        for art_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"  {art_type}: {count}")

        print("\nПримеры артефактов:")
        for i, artifact in enumerate(self.artifacts[:10], 1):
            print(f"\n{i}. [{artifact['type']}]")
            print(f"   OCR: {artifact['ocr_text']}")
            print(f"   Ожидалось: {artifact.get('expected_text', '-')}")
            print(f"   Подсказка: {artifact['suggestion']}")


def main():
    if len(sys.argv) < 2:
        print("Использование: python scripts/analyze_ocr_artifacts.py <receipt_id>")
        print("\nПримеры:")
        print("  python scripts/analyze_ocr_artifacts.py IMG_1292")
        print("  python scripts/analyze_ocr_artifacts.py PL_001")
        sys.exit(1)

    receipt_id = sys.argv[1]
    analyzer = ArtifactAnalyzer(receipt_id)
    result = analyzer.analyze()
    analyzer.print_summary()

    # Сохранение результата (опционально)
    output_path = PROJECT_ROOT / "data" / "analysis" / "ocr_artifacts" / f"{receipt_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Результат сохранен: {output_path}")


if __name__ == "__main__":
    main()
