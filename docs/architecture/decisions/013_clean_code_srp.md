# ADR-013: Clean Code и Single Responsibility Principle (SRP)

**Статус:** Утверждено  
**Дата:** 2025-12-31  
**Тип:** Фундаментальный архитектурный принцип

---

## Контекст

Проект обрабатывает чеки из 100+ локалей. Код должен быть:
- Поддерживаемым (maintainable)
- Расширяемым (extensible)
- Тестируемым (testable)
- Понятным (readable)

---

## Принцип

### Код - НЕ монолит

```
НЕ ТАК (монолит):
┌─────────────────────────────────────────┐
│            PreOCRProcessor              │
│                                         │
│  - load_image()                         │
│  - convert_to_grayscale()               │
│  - compress()                           │
│  - rotate()                             │
│  - crop()                               │
│  - denoise()                            │
│  - enhance_contrast()                   │
│  - ... 20 методов в одном классе        │
└─────────────────────────────────────────┘

А ТАК (SRP):
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Grayscale  │  │ Compressor  │  │   Rotator   │
│  Converter  │  │             │  │             │
│             │  │             │  │             │
│ ЦКП: ч/б    │  │ ЦКП: сжатие │  │ ЦКП: угол   │
└─────────────┘  └─────────────┘  └─────────────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │    Pipeline     │
               │  (оркестратор)  │
               └─────────────────┘
```

---

## Single Responsibility Principle (SRP)

### Определение

> **Каждый модуль/класс/функция отвечает ТОЛЬКО за одну задачу и имеет свой ЦКП.**

### Примеры из проекта

#### D1: Pre-OCR Elements

| Элемент | Файл | ЦКП | НЕ отвечает за |
|---------|------|-----|----------------|
| **GrayscaleConverter** | `grayscale.py` | Конвертация в ч/б (blue channel) | Сжатие, поворот, кроп |
| **ImageCompressor** | `image_compressor.py` | Адаптивное сжатие | Grayscale, поворот |
| **ImageRotator** | `rotator.py` | Коррекция угла | Сжатие, grayscale |
| **ImageCropper** | `cropper.py` | Обрезка границ | Сжатие, поворот |

#### D2: Parsing Components

| Компонент | ЦКП | НЕ отвечает за |
|-----------|-----|----------------|
| **LocaleDetector** | Определить локаль | Парсинг товаров |
| **StoreDetector** | Определить магазин | Определение локали |
| **MetadataExtractor** | Извлечь дату, итого | Парсинг товаров |
| **ItemExtractor** | Извлечь товары | Определение локали |
| **ChecksumValidator** | Валидация суммы | Извлечение данных |

---

## Правила

### 1. Один файл = Одна ответственность

```python
# ✓ ПРАВИЛЬНО: grayscale.py
class GrayscaleConverter:
    """Конвертирует в grayscale. Только это."""
    
    def process(self, image) -> GrayscaleResult:
        ...

# ✗ НЕПРАВИЛЬНО: image_processor.py
class ImageProcessor:
    """Делает всё: grayscale, сжатие, поворот, кроп..."""
    
    def process_all(self, image):
        self._to_grayscale()
        self._compress()
        self._rotate()
        self._crop()
        ...
```

### 2. Каждый элемент имеет свой ЦКП

```python
@dataclass
class GrayscaleResult:
    """ЦКП GrayscaleConverter"""
    image: np.ndarray
    was_converted: bool
    original_channels: int

@dataclass  
class CompressionResult:
    """ЦКП ImageCompressor"""
    image: np.ndarray
    scale_factor: float
    compressed_bytes: int
```

### 3. Pipeline = оркестратор элементов

```python
class PreOCRPipeline:
    """
    Оркестратор. Сам НЕ выполняет обработку.
    Только вызывает элементы в нужном порядке.
    """
    
    def __init__(self):
        self.grayscale = GrayscaleConverter()
        self.compressor = ImageCompressor()
        self.rotator = ImageRotator()
    
    def process(self, image):
        # Порядок определяется config, не хардкодом
        result = self.grayscale.process(image)
        result = self.compressor.compress(result.image)
        result = self.rotator.rotate(result.image)
        return result
```

### 4. Конфигурация вместо хардкода

```python
# ✗ НЕПРАВИЛЬНО: хардкод
class ImageCompressor:
    MAX_SIZE = 2200  # захардкожено
    QUALITY = 85     # захардкожено

# ✓ ПРАВИЛЬНО: конфиг
from config.settings import MAX_IMAGE_SIZE, JPEG_QUALITY

class ImageCompressor:
    def __init__(self):
        self.max_size = MAX_IMAGE_SIZE  # из конфига
        self.quality = JPEG_QUALITY     # из конфига
```

---

## Почему это важно

### 1. Тестируемость

```python
# Можно тестировать каждый элемент отдельно
def test_grayscale_converter():
    converter = GrayscaleConverter()
    result = converter.process(test_image)
    assert result.was_converted == True
    assert result.image.shape[2] == 1  # 1 канал

def test_compressor():
    compressor = ImageCompressor()
    result = compressor.compress(test_image, original_bytes)
    assert result.scale_factor < 1.0
```

### 2. Расширяемость

```python
# Добавить новый элемент = создать новый файл
# НЕ нужно трогать существующий код

# Новый элемент: Denoiser
class ImageDenoiser:
    """Убирает шум. Только это."""
    
    def process(self, image) -> DenoiseResult:
        ...

# Pipeline: просто добавить вызов
self.denoiser = ImageDenoiser()
```

### 3. Поддерживаемость

```python
# Баг в grayscale? 
# → Открываем grayscale.py
# → Фиксим
# → Другие элементы не затронуты

# В монолите:
# → Открываем image_processor.py (2000 строк)
# → Ищем где grayscale среди 20 методов
# → Риск сломать что-то другое
```

### 4. Понятность

```
Новый разработчик/AI смотрит на проект:

SRP структура:
  "grayscale.py - понятно, это про ч/б"
  "compressor.py - понятно, это про сжатие"
  
Монолит:
  "image_processor.py - 2000 строк, что где?"
```

---

## Структура директорий (пример D1)

```
src/extraction/
├── pre_ocr/
│   ├── elements/           # Отдельные элементы (SRP)
│   │   ├── grayscale.py    # ЦКП: конвертация в ч/б
│   │   ├── image_compressor.py  # ЦКП: сжатие
│   │   ├── rotator.py      # ЦКП: поворот
│   │   ├── cropper.py      # ЦКП: обрезка
│   │   └── denoiser.py     # ЦКП: удаление шума
│   │
│   ├── pipeline.py         # Оркестратор элементов
│   └── config.py           # Конфигурация пайплайна
│
├── ocr/
│   ├── google_vision.py    # ЦКП: вызов Google Vision API
│   └── adapter.py          # ЦКП: адаптация ответа к нашей схеме
│
└── domain/
    └── dto/
        └── raw_ocr_result.py  # Контракт D1 → D2
```

---

## Чеклист при создании нового кода

| Вопрос | Ожидаемый ответ |
|--------|-----------------|
| Этот класс/функция делает ОДНУ вещь? | ДА |
| Можно описать ЦКП одним предложением? | ДА |
| Можно протестировать изолированно? | ДА |
| Настройки вынесены в конфиг? | ДА |
| Если добавить функционал - нужен НОВЫЙ файл? | ДА |

---

## Антипаттерны (НЕ делать)

### 1. God Class

```python
# ✗ Класс который делает всё
class ReceiptProcessor:
    def load_image(self): ...
    def preprocess(self): ...
    def ocr(self): ...
    def parse(self): ...
    def validate(self): ...
    def categorize(self): ...
```

### 2. Смешение ответственностей

```python
# ✗ Grayscale + сжатие в одном методе
def process_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    compressed = cv2.resize(gray, (2200, 2200))  # WTF?
    return compressed
```

### 3. Хардкод вместо конфига

```python
# ✗ Магические числа в коде
if image.shape[0] > 2200:
    image = cv2.resize(image, (2200, int(2200 * aspect)))
```

---

## Связь с другими ADR

- **ADR-001:** Разделение на домены (SRP на уровне доменов)
- **ADR-002:** ЦКП доменов (каждый домен = свой ЦКП)
- **ADR-010:** Иерархия конфигов (конфиг вместо хардкода)

---

## Резюме

| Принцип | Описание |
|---------|----------|
| **Не монолит** | Код разбит на маленькие модули |
| **SRP** | Один модуль = одна ответственность |
| **ЦКП каждого элемента** | Чёткий результат, который элемент гарантирует |
| **Конфиг вместо хардкода** | Настройки вынесены, не зашиты в код |
| **Pipeline = оркестратор** | Сам не обрабатывает, только вызывает элементы |

---

## История изменений

| Дата | Изменение |
|------|-----------|
| 2025-12-31 | Создан документ. Утверждены принципы Clean Code и SRP. |
