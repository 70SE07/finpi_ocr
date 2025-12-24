import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import cv2
import numpy as np
from loguru import logger

# #region agent log
_DEBUG_LOG_PATH = "/Users/sergejevsukov/Мой диск/SaaS/FinPi/finpi_parser_photo/.cursor/debug.log"
# #endregion


@dataclass
class DeskewResult:
    """Результат выравнивания изображения."""

    image: np.ndarray
    angle: float  # Малый наклон (1-15°)
    was_rotated: bool
    rotation_90: int = 0  # Крупный поворот (0, 90, 180, 270)
    steps_applied: list[str] = field(default_factory=list)  # Список применённых шагов для отладки


class DeskewProcessor:
    """
    Класс для автоматического выравнивания (deskewing) изображения чека.
    Использует координаты слов для определения прецизионного угла наклона.
    """

    def __init__(self, min_angle_threshold: float = 0.1):
        self.min_angle_threshold = min_angle_threshold

    def detect_orientation_90(self, words: list[Any]) -> int:
        """
        [LOW-LEVEL] Определяет нужна ли коррекция ориентации на 90°/180°/270°.

        ⚠️ ВНИМАНИЕ: Для полного выравнивания используйте process_full_orientation()!
        Этот метод НЕ должен вызываться отдельно, если нужен малый наклон.
        Вызывайте ТОЛЬКО если вам нужен только крупный поворот.

        Анализирует углы слов и определяет, в какой ориентации находится изображение.

        Returns:
            0 - изображение в правильной ориентации
            90 - нужно повернуть на 90° по часовой стрелке
            180 - нужно повернуть на 180°
            270 - нужно повернуть на 270° по часовой стрелке (или 90° против)
        """
        angles = []

        for word in words:
            try:
                if hasattr(word, "bounding_box") and hasattr(word.bounding_box, "vertices"):
                    v = word.bounding_box.vertices
                elif hasattr(word, "bounding_poly") and hasattr(word.bounding_poly, "vertices"):
                    v = word.bounding_poly.vertices
                else:
                    continue

                if len(v) < 2:
                    continue

                dx = v[1].x - v[0].x
                dy = v[1].y - v[0].y

                # Игнорируем очень короткие слова
                if abs(dx) < 10 and abs(dy) < 10:
                    continue

                angle = np.degrees(np.arctan2(dy, dx))
                angles.append(angle)

            except (AttributeError, IndexError):
                continue

        if not angles:
            return 0

        median_angle = np.median(angles)

        # Определяем квадрант угла
        # Нормальная ориентация: угол около 0° (-15° до +15°)
        # Повёрнуто на 90° CW: угол около -90° (-105° до -75°) или около 90°
        # Повёрнуто на 180°: угол около ±180°
        # Повёрнуто на 270° CW (90° CCW): угол около 90° (75° до 105°)

        if -15 <= median_angle <= 15:
            return 0  # Правильная ориентация
        elif -105 <= median_angle <= -75:
            return 90  # Нужно повернуть на 90° CW
        elif 75 <= median_angle <= 105:
            return 270  # Нужно повернуть на 270° CW (90° CCW)
        elif abs(median_angle) >= 165:
            return 180  # Нужно повернуть на 180°
        else:
            return 0  # Не определено, оставляем как есть

    def rotate_90(self, image: np.ndarray, rotation: int) -> np.ndarray:
        """
        Поворачивает изображение на 90°, 180° или 270°.

        Args:
            image: Входное изображение
            rotation: 0, 90, 180 или 270

        Returns:
            Повёрнутое изображение
        """
        if rotation == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif rotation == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            return image

    def calculate_skew_angle(self, words: list[Any]) -> float:
        """
        [LOW-LEVEL] Вычисляет медианный угол наклона текстовых строк на основе координат слов.

        ⚠️ ВНИМАНИЕ: Вызывайте ТОЛЬКО после исправления крупного поворота (90°/180°/270°)!
        Для полного выравнивания используйте process_full_orientation()!

        Этот метод определяет малый наклон (1-15°) и работает корректно только
        если изображение уже в правильной ориентации (не повёрнуто на 90°/180°/270°).
        """
        # #region agent log
        try:
            with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "id": f"log_{int(datetime.now().timestamp() * 1000)}_calc_start",
                            "timestamp": int(datetime.now().timestamp() * 1000),
                            "location": "deskew.py:26",
                            "message": "calculate_skew_angle START",
                            "data": {"words_count": len(words), "min_angle_threshold": self.min_angle_threshold},
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "A,D",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion

        angles = []
        words_processed = 0
        words_skipped_no_vertices = 0
        words_skipped_dx_too_small = 0
        words_skipped_angle_too_large = 0
        words_added = 0

        for word in words:
            try:
                # Поддержка разных видов объектов слова:
                # - TEXT_DETECTION: word.bounding_poly.vertices
                # - DOCUMENT_TEXT_DETECTION: word.bounding_box.vertices
                # - DTO: word.vertices
                if hasattr(word, "bounding_box") and hasattr(word.bounding_box, "vertices"):
                    # DOCUMENT_TEXT_DETECTION формат (предпочтительный для deskew!)
                    v = word.bounding_box.vertices
                elif hasattr(word, "bounding_poly") and hasattr(word.bounding_poly, "vertices"):
                    # TEXT_DETECTION формат (axis-aligned, менее точный)
                    v = word.bounding_poly.vertices
                elif hasattr(word, "vertices"):
                    v = word.vertices
                else:
                    words_skipped_no_vertices += 1
                    continue

                if len(v) < 4:
                    words_skipped_no_vertices += 1
                    continue

                words_processed += 1

                # Используем нижнюю границу bounding box для более точного определения угла
                # v[0] = верхний левый, v[1] = верхний правый
                # v[2] = нижний правый, v[3] = нижний левый
                # Используем нижнюю границу (v[2] и v[3]) или верхнюю (v[0] и v[1])
                # Пробуем оба варианта и выбираем более надёжный

                # Вариант 1: Верхняя граница
                dx_top = v[1].x - v[0].x
                dy_top = v[1].y - v[0].y

                # Вариант 2: Нижняя граница (более надёжна для определения наклона)
                dx_bottom = v[2].x - v[3].x
                dy_bottom = v[2].y - v[3].y

                # Используем нижнюю границу, если она достаточно длинная, иначе верхнюю
                if abs(dx_bottom) > 15:
                    dx = dx_bottom
                    dy = dy_bottom
                    edge_used = "bottom"
                elif abs(dx_top) > 15:
                    dx = dx_top
                    dy = dy_top
                    edge_used = "top"
                else:
                    words_skipped_dx_too_small += 1
                    continue

                # #region agent log
                if words_processed <= 10:  # Логируем первые 10 слов для анализа
                    try:
                        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                            f.write(
                                json.dumps(
                                    {
                                        "id": f"log_{int(datetime.now().timestamp() * 1000)}_word_{words_processed}",
                                        "timestamp": int(datetime.now().timestamp() * 1000),
                                        "location": "deskew.py:66",
                                        "message": "Word processing",
                                        "data": {
                                            "word_idx": words_processed,
                                            "dx": float(dx),
                                            "dy": float(dy),
                                            "edge_used": edge_used,
                                            "dx_top": float(dx_top),
                                            "dy_top": float(dy_top),
                                            "dx_bottom": float(dx_bottom),
                                            "dy_bottom": float(dy_bottom),
                                        },
                                        "sessionId": "debug-session",
                                        "runId": "run2",
                                        "hypothesisId": "C",
                                    }
                                )
                                + "\n"
                            )
                    except Exception:
                        pass
                # #endregion

                angle = np.degrees(np.arctan2(dy, dx))
                # #region agent log
                if words_processed <= 10:
                    try:
                        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                            f.write(
                                json.dumps(
                                    {
                                        "id": f"log_{int(datetime.now().timestamp() * 1000)}_angle_calc_{words_processed}",
                                        "timestamp": int(datetime.now().timestamp() * 1000),
                                        "location": "deskew.py:87",
                                        "message": "Angle calculated",
                                        "data": {
                                            "word_idx": words_processed,
                                            "angle_degrees": float(angle),
                                            "abs_angle": abs(angle),
                                            "edge_used": edge_used,
                                        },
                                        "sessionId": "debug-session",
                                        "runId": "run2",
                                        "hypothesisId": "C",
                                    }
                                )
                                + "\n"
                            )
                    except Exception:
                        pass
                # #endregion
                if abs(angle) < 15:
                    angles.append(angle)
                    words_added += 1
                else:
                    words_skipped_angle_too_large += 1
            except (AttributeError, IndexError):
                words_skipped_no_vertices += 1
                continue

        # Фильтруем нулевые углы перед вычислением медианы для более точного результата
        non_zero_angles = [a for a in angles if abs(a) > 0.01]

        if non_zero_angles:
            # Используем медиану ненулевых углов
            median_angle = float(np.median(non_zero_angles))
        elif angles:
            # Если все углы нулевые, возвращаем 0.0
            median_angle = 0.0
        else:
            median_angle = 0.0

        # #region agent log
        try:
            with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "id": f"log_{int(datetime.now().timestamp() * 1000)}_calc_end",
                            "timestamp": int(datetime.now().timestamp() * 1000),
                            "location": "deskew.py:107",
                            "message": "calculate_skew_angle END",
                            "data": {
                                "words_processed": words_processed,
                                "words_skipped_no_vertices": words_skipped_no_vertices,
                                "words_skipped_dx_too_small": words_skipped_dx_too_small,
                                "words_skipped_angle_too_large": words_skipped_angle_too_large,
                                "words_added": words_added,
                                "angles_count": len(angles),
                                "non_zero_angles_count": len(non_zero_angles),
                                "median_angle": median_angle,
                                "angles_sample": [float(a) for a in angles[:10]] if angles else [],
                                "non_zero_angles_sample": (
                                    [float(a) for a in non_zero_angles[:10]] if non_zero_angles else []
                                ),
                            },
                            "sessionId": "debug-session",
                            "runId": "run2",
                            "hypothesisId": "A,B,C,D",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion

        return median_angle

    def rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """
        Поворачивает изображение на заданный угол.
        """
        # #region agent log
        try:
            with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "id": f"log_{int(datetime.now().timestamp() * 1000)}_rotate_start",
                            "timestamp": int(datetime.now().timestamp() * 1000),
                            "location": "deskew.py:59",
                            "message": "rotate_image START",
                            "data": {
                                "angle": float(angle),
                                "abs_angle": abs(angle),
                                "min_angle_threshold": self.min_angle_threshold,
                                "image_shape": list(image.shape),
                            },
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "B,E",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion

        if abs(angle) < self.min_angle_threshold:
            # #region agent log
            try:
                with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "id": f"log_{int(datetime.now().timestamp() * 1000)}_rotate_skipped",
                                "timestamp": int(datetime.now().timestamp() * 1000),
                                "location": "deskew.py:63",
                                "message": "rotate_image SKIPPED (angle too small)",
                                "data": {
                                    "angle": float(angle),
                                    "abs_angle": abs(angle),
                                    "min_angle_threshold": self.min_angle_threshold,
                                },
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "B",
                            }
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion
            return image

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        # #region agent log
        try:
            with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "id": f"log_{int(datetime.now().timestamp() * 1000)}_rotate_end",
                            "timestamp": int(datetime.now().timestamp() * 1000),
                            "location": "deskew.py:70",
                            "message": "rotate_image END",
                            "data": {
                                "angle": float(angle),
                                "rotated_shape": list(rotated.shape),
                                "original_shape": list(image.shape),
                            },
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "E",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion

        return rotated

    def process_with_words(self, image: np.ndarray, words: list[Any]) -> DeskewResult:
        """
        Выравнивает изображение, используя список слов.
        """
        angle = self.calculate_skew_angle(words)
        if abs(angle) < self.min_angle_threshold:
            # #region agent log
            try:
                with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "id": f"log_{int(datetime.now().timestamp() * 1000)}_process_no_rotate",
                                "timestamp": int(datetime.now().timestamp() * 1000),
                                "location": "deskew.py:78",
                                "message": "process_with_words NO ROTATION",
                                "data": {
                                    "angle": float(angle),
                                    "abs_angle": abs(angle),
                                    "min_angle_threshold": self.min_angle_threshold,
                                    "was_rotated": False,
                                },
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "B",
                            }
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # #endregion
            return DeskewResult(image=image, angle=angle, was_rotated=False)

        rotated = self.rotate_image(image, angle)
        # #region agent log
        try:
            with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "id": f"log_{int(datetime.now().timestamp() * 1000)}_process_rotated",
                            "timestamp": int(datetime.now().timestamp() * 1000),
                            "location": "deskew.py:82",
                            "message": "process_with_words ROTATED",
                            "data": {
                                "angle": float(angle),
                                "was_rotated": True,
                                "original_shape": list(image.shape),
                                "rotated_shape": list(rotated.shape),
                            },
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "E",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        return DeskewResult(image=rotated, angle=angle, was_rotated=True)

    async def process_full_orientation(
        self,
        image: np.ndarray,
        words: list[Any],
        update_words_callback: Callable[[np.ndarray], Awaitable[list[Any]]] | None = None,
    ) -> DeskewResult:
        """
        ГАРАНТИРОВАННЫЙ ПАЙПЛАЙН выравнивания изображения.

        Порядок операций (НЕ МЕНЯТЬ):
        1. Крупный поворот (90°/180°/270°) - ДО малого наклона
           Причина: если изображение повёрнуто на 90°, малый наклон вычисляется некорректно
        2. Малый наклон (1-15°) - ПОСЛЕ крупного поворота
           Причина: после исправления ориентации можно точно определить малый наклон

        Args:
            image: Исходное изображение (BGR, numpy array)
            words: Аннотации слов от DOCUMENT_TEXT_DETECTION (для определения углов)
            update_words_callback: Async функция для обновления аннотаций после поворота.
                                  Должна принимать повёрнутое изображение и возвращать
                                  обновлённый список слов (вызывает новый OCR).
                                  ОБЯЗАТЕЛЬНА если требуется крупный поворот!
                                  Может быть None, если крупный поворот не требуется.

        Returns:
            DeskewResult с выровненным изображением и информацией о применённых шагах

        Raises:
            ValueError: Если требуется крупный поворот, но callback не предоставлен
        """
        steps_applied = []
        rotation_90 = 0
        final_angle = 0.0
        was_rotated = False

        # ШАГ 1: Крупный поворот (90°/180°/270°)
        logger.info("[Deskew Step 1/2] Определение крупного поворота...")
        rotation_90 = self.detect_orientation_90(words)

        if rotation_90 != 0:
            logger.info(f"[Deskew Step 1/2] Обнаружен крупный поворот: {rotation_90}°")

            # Валидация: callback обязателен после крупного поворота
            if update_words_callback is None:
                raise ValueError(
                    f"update_words_callback обязателен после крупного поворота ({rotation_90}°)! "
                    "После поворота координаты слов меняются, нужен новый OCR для точного определения малого наклона."
                )

            # Применяем крупный поворот
            image = self.rotate_90(image, rotation_90)
            steps_applied.append(f"rotation_90_{rotation_90}")
            was_rotated = True

            logger.info(
                f"[Deskew Step 1/2] ✓ Применён поворот {rotation_90}° (размер: {image.shape[1]}x{image.shape[0]})"
            )

            # Обновляем аннотации после поворота
            logger.info("[Deskew Step 1/2] Обновление аннотаций после крупного поворота...")
            words = await update_words_callback(image)
            logger.info(f"[Deskew Step 1/2] ✓ Аннотации обновлены ({len(words)} слов)")
        else:
            logger.info("[Deskew Step 1/2] Крупный поворот не требуется")

        # ШАГ 2: Малый наклон (1-15°)
        logger.info("[Deskew Step 2/2] Определение малого наклона...")
        final_angle = self.calculate_skew_angle(words)

        if abs(final_angle) > self.min_angle_threshold:
            logger.info(f"[Deskew Step 2/2] Обнаружен малый наклон: {final_angle:.2f}°")

            # Применяем малый наклон
            image = self.rotate_image(image, final_angle)
            steps_applied.append(f"skew_{final_angle:.2f}")
            was_rotated = True

            logger.info(
                f"[Deskew Step 2/2] ✓ Применён наклон {final_angle:.2f}° (размер: {image.shape[1]}x{image.shape[0]})"
            )

            # Обновляем аннотации после малого наклона (для последующего кропа)
            if update_words_callback:
                logger.info("[Deskew Step 2/2] Обновление аннотаций после малого наклона...")
                words = await update_words_callback(image)
                logger.info(f"[Deskew Step 2/2] ✓ Аннотации обновлены ({len(words)} слов)")
        else:
            logger.info(
                f"[Deskew Step 2/2] Малый наклон не требуется (угол: {final_angle:.2f}°, порог: {self.min_angle_threshold}°)"
            )

        if not was_rotated:
            logger.info("[Deskew] Выравнивание не требуется, изображение уже в правильной ориентации")
        else:
            logger.info(f"[Deskew] ✓ Выравнивание завершено. Применённые шаги: {', '.join(steps_applied)}")

        return DeskewResult(
            image=image,
            angle=final_angle,
            was_rotated=was_rotated,
            rotation_90=rotation_90,
            steps_applied=steps_applied,
        )
