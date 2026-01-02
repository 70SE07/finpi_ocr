# Hypothesis 001: 180° Rotation Optimization

## Status: PROPOSED
**Created:** 2023-12-23  
**Author:** AI Assistant + User  

---

## Problem Statement

When a receipt image is upside down (rotated 180°):
- Google Vision OCR **correctly reads** individual words/characters
- BUT the **line order is reversed** (bottom-to-top instead of top-to-bottom)
- Parser expects: `Store Name → Items → Total`
- Parser receives: `Total → Items → Store Name`

This causes parsing failures.

---

## Current Approach (Naive)

```
1. Pre-OCR processing (compress, grayscale, deskew)
2. OCR #1 → get annotations
3. Detect 180° rotation using annotations
4. If rotated → physically rotate image 180°
5. OCR #2 → get correct annotations
```

**Downside:** Two OCR API calls = 2x cost, 2x latency

---

## Proposed Optimization

Instead of making a second OCR call after rotating the image, we can **mathematically transform** the annotations from OCR #1:

### Algorithm

```python
def invert_annotations_180(annotations: list, image_height: int, image_width: int) -> list:
    """
    Transform annotations as if image was rotated 180°.
    
    For each annotation:
    1. Invert Y coordinates: new_y = image_height - original_y
    2. Invert X coordinates: new_x = image_width - original_x
    3. Reverse the order of all annotations
    """
    inverted = []
    
    for ann in annotations:
        new_vertices = []
        for vertex in ann.bounding_poly.vertices:
            new_vertices.append({
                'x': image_width - vertex.x,
                'y': image_height - vertex.y
            })
        
        inverted.append({
            'description': ann.description,
            'bounding_poly': {'vertices': new_vertices}
        })
    
    # Reverse order (first becomes last)
    return inverted[::-1]
```

### Benefits

| Metric | Two OCR Calls | Optimization |
|--------|---------------|--------------|
| OCR API calls | 2 | 1 |
| Latency | ~2x | ~1x |
| Cost | ~2x | ~1x |
| Accuracy | Same | Same (theoretical) |

---

## Validation Plan

### Test Cases

1. **Baseline:** Take 10 upside-down receipts, process with two OCR calls
2. **Optimized:** Same receipts, process with one OCR call + coordinate inversion
3. **Compare:** 
   - Parsed item names
   - Parsed prices
   - Parsed totals
   - Line order

### Success Criteria

- 100% match between baseline and optimized results
- No parsing errors introduced by optimization

---

## Edge Cases to Consider

1. **Multi-line text blocks:** Do they need special handling?
2. **Word-level vs paragraph-level annotations:** Which to use?
3. **Confidence scores:** Are they affected by rotation?
4. **Bounding box precision:** Any rounding errors after transformation?

---

## Implementation Steps

1. [ ] Create test dataset of 10+ upside-down receipts
2. [ ] Implement `invert_annotations_180()` function
3. [ ] Run A/B test: baseline vs optimized
4. [ ] Measure accuracy and performance
5. [ ] If successful, integrate into pipeline

---

## Related Files

- `src/pre_ocr/deskew_cv.py` - CV-based deskew (handles 90°, not 180°)
- `src/pre_ocr/deskew.py` - OCR-based deskew (uses annotations)
- `src/extraction/infrastructure/ocr/google_vision_ocr.py` - OCR client

---

## Notes

This optimization is especially valuable for batch processing where:
- Many receipts may be upside down
- API costs are a concern
- Latency matters (real-time processing)
