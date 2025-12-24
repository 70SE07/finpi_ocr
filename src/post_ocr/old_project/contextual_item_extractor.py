import re
from typing import Any, Optional

from dci.post_ocr.context_line import ContextLine
from dci.post_ocr.line_grouping import LineData, WordData


class ContextualItemExtractor:
    r"""
    Extracts items using anchor-based logic (Price Anchoring).
    Systemic approach for 100+ locales.
    """

    def __init__(self, decimal_separator: str = ","):
        self.decimal_separator = decimal_separator

    def extract(self, lines: list[LineData]) -> list[dict[str, Any]]:
        # 1. Normalization
        if self.decimal_separator == ",":
            for line in lines:
                for word in line.words:
                    if re.match(r"^-?\d+\.\d{2}$", word.text):
                        word.text = word.text.replace(".", ",")
        
        # 2. Splitter Pre-pass
        processed_lines, index_mapping = self._pre_pass_split_lines(lines)
        self._index_mapping = index_mapping
        
        # 3. Preprocessing
        context_lines = [ContextLine.analyze(line, i, self.decimal_separator) for i, line in enumerate(processed_lines)]

        # 4. Dead Zone
        total_boundary_idx = len(context_lines)
        total_keywords = ["zu zahlen", "summe", "total", "gesamt", "итого", "сумма", "betrag", "brutto", "netto", "mwst"]
        for i, cl in enumerate(context_lines):
            if any(k in cl.text.lower() for k in total_keywords):
                total_boundary_idx = i
                break

        items = []
        consumed_indices = set()
        
        # --- PHASE 1: High Confidence ---
        for i, line in enumerate(context_lines):
            if i in consumed_indices or i > total_boundary_idx: continue
                
            if line.is_full_item:
                print(f"DEBUG: Line {i} is FULL: {line.text}")
                item = self._extract_full_item_with_qty(line)
                if not item:
                    print(f"DEBUG: full_qty failed for line {i}, trying one_liner")
                    item = self._extract_one_liner(line)
                
                if item:
                    print(f"DEBUG: Extracted item from FULL line {i}: {item['name']}")
                    kg_item = self._extract_kg_two_liner(context_lines, i, consumed_indices)
                    if kg_item: item = kg_item
                    
                    last_idx = max(item.get("line_indices", [i]))
                    discount = self._find_discount_below(context_lines, last_idx, consumed_indices)
                    if discount > 0:
                        item["discount"] = f"{discount:.2f}"
                        if last_idx + 1 < len(context_lines):
                             item["line_indices"].append(last_idx + 1)

                    items.append(item)
                    for idx in item.get("line_indices", [i]): consumed_indices.add(idx)
                continue
                
            if line.is_valid_anchor:
                item = self._extract_kg_two_liner(context_lines, i, consumed_indices)
                if not item:
                    item = self._collect_item_upwards(context_lines, i, consumed_indices, is_recovery=False)
                
                if item:
                    last_idx = max(item.get("line_indices", [i]))
                    discount = self._find_discount_below(context_lines, last_idx, consumed_indices)
                    if discount > 0:
                        item["discount"] = f"{discount:.2f}"
                        if last_idx + 1 < len(context_lines):
                             item["line_indices"].append(last_idx + 1)
                    
                    items.append(item)
                    for idx in item.get("line_indices", [i]): consumed_indices.add(idx)

        # --- PHASE 2: Recovery ---
        for i, line in enumerate(context_lines):
            if i in consumed_indices or i > total_boundary_idx: continue
            if line.is_soft_price and not line.is_valid_anchor and not line.is_noise:
                item = self._collect_item_upwards(context_lines, i, consumed_indices, is_recovery=True)
                if item:
                    last_idx = max(item.get("line_indices", [i]))
                    discount = self._find_discount_below(context_lines, last_idx, consumed_indices)
                    if discount > 0:
                        item["discount"] = f"{discount:.2f}"
                        if last_idx + 1 < len(context_lines):
                             item["line_indices"].append(last_idx + 1)
                    items.append(item)
                    for idx in item.get("line_indices", [i]): consumed_indices.add(idx)

        # --- PHASE 3: Remaining Discounts ---
        for i, line in enumerate(context_lines):
            if i in consumed_indices or i > total_boundary_idx: continue
            if line.is_discount_marker and line.parsed_value:
                val = -abs(line.parsed_value)
                item = self._create_item(line, name=line.text, price=val, qty=1.0, total=val, line_indices=[i])
                if item:
                    items.append(item)
                    consumed_indices.add(i)

        items.sort(key=lambda x: x.get("line_indices", [0])[0])
        
        # [DEBUG]
        print(f"DEBUG: Extractor returning {len(items)} items")
        for idx, it in enumerate(items):
             print(f"DEBUG: Item {idx+1}: {it['name']} ({it['total']}) Lines: {it.get('line_indices')}")

        return items

    def _collect_item_upwards(self, context_lines, anchor_idx, consumed_indices, max_lookback=5, is_recovery=False):
        anchor_line = context_lines[anchor_idx]
        if is_recovery and not anchor_line.parsed_value:
            match = re.search(rf'(-?\d+[{re.escape(self.decimal_separator)}]\d{{0,2}})', anchor_line.text)
            if match:
                try:
                    p = match.group(1).replace(self.decimal_separator, '.')
                    if '.' not in p: p = f"{float(p):.2f}"
                    anchor_line.parsed_value = float(p)
                except: pass

        item = self._extract_one_liner(anchor_line, is_recovery=is_recovery)
        if item: return item
        item = self._extract_staircase(context_lines, anchor_idx, consumed_indices, max_lookback, is_recovery=is_recovery)
        if item: return item
        item = self._extract_math_hybrid(context_lines, anchor_idx, consumed_indices, is_recovery=is_recovery)
        if item: return item
        item = self._extract_kg_two_liner(context_lines, anchor_idx, consumed_indices)
        if item: return item
        return self._extract_simple_two_liner(context_lines, anchor_idx, consumed_indices, is_recovery=is_recovery)

    def _extract_one_liner(self, anchor_line, is_recovery=False):
        if not (anchor_line.is_full_item or anchor_line.is_price_candidate or (is_recovery and anchor_line.is_soft_price)): return None
        text = anchor_line.text.strip()
        if anchor_line.is_full_item:
            full_match = re.search(rf"^(.+?)\s+(-?\d+[{re.escape(self.decimal_separator)}]\d{{2}})\s*([A-Z0-9*]?.*)$", text, re.IGNORECASE)
            if full_match:
                name = self._clean_name(full_match.group(1))
                if name and len(name) > 1:
                    return self._create_item(anchor_line, name=name, price=anchor_line.parsed_value, qty=1.0, total=anchor_line.parsed_value, line_indices=[anchor_line.original_index])
        if anchor_line.is_price_candidate or (is_recovery and anchor_line.is_soft_price):
            price_match = re.search(rf"(.+?)\s+(-?\d+[{re.escape(self.decimal_separator)}]\d{{0,2}})\s*([A-Z0-9*]?.*)$", text, re.IGNORECASE)
            if price_match:
                name = self._clean_name(price_match.group(1))
                if name and len(name) > 1:
                    p = anchor_line.parsed_value
                    if p is None and is_recovery:
                        try: p = float(price_match.group(2).replace(self.decimal_separator, '.'))
                        except: p = 0.0
                    if p: return self._create_item(anchor_line, name=name, price=p, qty=1.0, total=p, line_indices=[anchor_line.original_index])
        return None

    def _extract_full_item_with_qty(self, anchor_line):
        if not anchor_line.is_full_item and not anchor_line.is_math_pattern: return None
        text = anchor_line.text.strip()
        # [СИСТЕМНОЕ УСИЛЕНИЕ]: Максимально гибкий паттерн. Берем последнюю цену как Total.
        # Группы: 1:Name, 2:Price1, 3:Qty, 4:Total (последняя цена в строке)
        full_qty_pattern = re.compile(r"(.+?)\s+([\d\s.,]+?)\s*[xX×х]\s*([\d\s.,]+?)\s+.*?(\d+[\s,.]\d{2})(?:\s+[A-Z0-9*]*)?$", re.IGNORECASE)
        match = full_qty_pattern.search(text)
        if match:
            try:
                name = self._clean_name(match.group(1))
                if name and len(name) > 1 and not re.match(r"^[\d\s.,]+$", name):
                    def clean_v(s):
                        d = re.sub(r"[^\d]", "", s)
                        return float(d[:-2] + "." + d[-2:]) if len(d) >= 3 else float(d)
                    p1 = clean_v(match.group(2))
                    qty_str = re.sub(r"[^\d.,]", "", match.group(3)).replace(",", ".")
                    qty = float(qty_str) if qty_str else 1.0
                    p2 = clean_v(match.group(4))
                    # Верификация: p1 * qty = p2 (с допуском)
                    if abs(round(p1 * qty, 2) - p2) < 0.15 and p2 > 0:
                        return self._create_item(anchor_line, name=name, price=p1, qty=qty, total=p2, line_indices=[anchor_line.original_index])
            except: pass
        return None

    def _extract_simple_two_liner(self, context_lines, anchor_idx, consumed_indices, max_lookback=3, is_recovery=False):
        if anchor_idx == 0: return None
        anchor_line = context_lines[anchor_idx]; p = anchor_line.parsed_value
        if not p: return None
        for i in range(anchor_idx - 1, max(-1, anchor_idx - max_lookback - 1), -1):
            if i in consumed_indices: break
            line = context_lines[i]
            if line.is_price_candidate or (line.is_soft_price and not line.is_noise): break
            if line.is_noise: continue
            if line.is_text_candidate:
                name = self._clean_name(line.text)
                if name and len(name) > 1:
                    return self._create_item(anchor_line, name=name, price=p, qty=1.0, total=p, line_indices=[line.original_index, anchor_line.original_index])
        return None

    def _extract_math_hybrid(self, context_lines, anchor_idx, consumed_indices, max_lookback=5, is_recovery=False):
        anchor_line = context_lines[anchor_idx]; total = anchor_line.parsed_value
        if not total: return None
        for i in range(anchor_idx - 1, max(-1, anchor_idx - max_lookback - 1), -1):
            if i in consumed_indices: break
            prev_line = context_lines[i]
            if (prev_line.is_price_candidate or (prev_line.is_soft_price and not prev_line.is_noise)) and i != anchor_idx: break
            if prev_line.is_noise and not prev_line.is_math_pattern: continue
            if prev_line.is_math_pattern or " x " in prev_line.text.lower():
                math_match = re.search(rf"(.+?)\s+(-?\d+[{re.escape(self.decimal_separator)}]\d{{2}})\s*[xXх]\s*(\d+[.,]?\d*)", prev_line.text, re.IGNORECASE)
                if math_match:
                    try:
                        name = self._clean_name(math_match.group(1))
                                    if name and len(name) > 1:
                            p1 = float(math_match.group(2).replace(self.decimal_separator, "."))
                            qty = float(math_match.group(3).replace(",", "."))
                            if abs(round(p1 * qty, 2) - total) < 0.05:
                                return self._create_item(anchor_line, name=name, price=p1, qty=qty, total=total, line_indices=[prev_line.original_index, anchor_line.original_index])
                    except: pass
                break
        return None

    def _find_discount_below(self, context_lines, anchor_idx, consumed_indices):
        next_idx = anchor_idx + 1
        if next_idx >= len(context_lines) or next_idx in consumed_indices: return 0.0
        line = context_lines[next_idx]
        if line.is_discount_marker and line.parsed_value:
            consumed_indices.add(next_idx); return abs(line.parsed_value)
        return 0.0

    def _extract_kg_two_liner(self, context_lines, anchor_idx, consumed_indices):
        anchor_line = context_lines[anchor_idx]; total = anchor_line.parsed_value
        if not total or anchor_idx + 1 >= len(context_lines): return None
        next_line = context_lines[anchor_idx+1]
        if anchor_idx + 1 in consumed_indices: return None
        kg_pattern = re.compile(rf"(\d+[{re.escape(self.decimal_separator)}]\d+)\s*(?:kg|g|lb|stk|l|ml|stk\.)\s*x\s*(\d+[{re.escape(self.decimal_separator)}]\d+)", re.IGNORECASE)
        match = kg_pattern.search(next_line.text)
        if match:
            try:
                w = float(match.group(1).replace(self.decimal_separator, "."))
                p = float(match.group(2).replace(self.decimal_separator, "."))
                if abs(round(w * p, 2) - total) < 0.15 or next_line.is_metadata_line:
                    price_str = f"{total:.2f}".replace(".", self.decimal_separator)
                    name = self._clean_name(anchor_line.text.split(price_str)[0])
                    if name:
                        consumed_indices.add(anchor_idx+1)
                        return self._create_item(anchor_line, name=name, price=p, qty=w, total=total, line_indices=[anchor_line.original_index, next_line.original_index])
            except: pass
            return None

    def _extract_staircase(self, context_lines, anchor_idx, consumed_indices, max_lookback=5, is_recovery=False):
        anchor_line = context_lines[anchor_idx]; total = anchor_line.parsed_value
        if not total: return None
        qty = None; unit_price = None; name_line = None; indices = [anchor_line.original_index]
        for i in range(anchor_idx - 1, max(0, anchor_idx - max_lookback) - 1, -1):
            if i in consumed_indices: break
            line = context_lines[i]
            if line.is_price_candidate and (unit_price is not None or line.is_full_item): break
            text = line.text.strip()
            if qty is None:
                m1 = re.match(r"^\s*(\d+)\s*(?:Stk|x)?\s*$", text, re.IGNORECASE)
                m2 = re.match(r"^\s*x\s*(\d+)\s*$", text, re.IGNORECASE)
                if m1: qty = float(m1.group(1)); indices.append(line.original_index); continue
                if m2: qty = float(m2.group(1)); indices.append(line.original_index); continue
            if unit_price is None:
                m3 = re.search(rf"(\d+[{re.escape(self.decimal_separator)}]\d{{1,2}})\s*x", text)
                if m3: unit_price = float(m3.group(1).replace(self.decimal_separator, ".")); indices.append(line.original_index); continue
                if line.is_price_candidate and not line.is_full_item:
                    c = re.sub(rf"\d+[{re.escape(self.decimal_separator)}]\d{{2}}", "", text).strip()
                    if len(c) < 3: unit_price = line.parsed_value; indices.append(line.original_index); continue
            if name_line is None and line.is_text_candidate and not line.is_noise:
                if qty is not None or unit_price is not None: name_line = line; indices.append(line.original_index)
        if qty and unit_price and name_line and abs(round(unit_price * qty, 2) - total) < 0.05:
            return self._create_item(anchor_line, name=self._clean_name(name_line.text), price=unit_price, qty=qty, total=total, line_indices=indices)
        return None

    def _split_line_by_layers(self, line_data):
        words = sorted(line_data.words, key=lambda w: (w.x_left, w.x_right))
        if len(words) < 4: return None
        l1 = []; l2 = []; i = 0; overlaps = 0
        prices = [w for w in words if re.search(rf'\d+[{re.escape(self.decimal_separator)}]\d{{2}}', w.text)]
        has_overlap = False
        for j in range(len(prices)-1):
            p1, p2 = prices[j], prices[j+1]
            if min(p1.x_right, p2.x_right) - max(p1.x_left, p2.x_left) > min(p1.width, p2.width) * 0.7: has_overlap = True; break
        while i < len(words):
            w1 = words[i]
            if i + 1 < len(words):
                w2 = words[i+1]; overlap = min(w1.x_right, w2.x_right) - max(w1.x_left, w2.x_left)
                if overlap > min(w1.width, w2.width) * 0.3 or (has_overlap and i % 2 == 0):
                    l1.append(w1); l2.append(w2); overlaps += 1; i += 2; continue
            l1.append(w1); i += 1
        if overlaps >= 1:
            p1 = LineData(words=l1); p2 = LineData(words=l2)
            if ContextLine.analyze(p1, 0, self.decimal_separator).price_ranges and ContextLine.analyze(p2, 0, self.decimal_separator).price_ranges: return [p1, p2]
        return None

    def _split_line_by_columns(self, line_data, context_line):
        if len(context_line.price_ranges) < 2: return None
        words = sorted(line_data.words, key=lambda w: w.x_left); gaps = []
        for i in range(len(words)-1): gaps.append((words[i+1].x_left - words[i].x_right, i))
        gaps.sort(key=lambda x: x[0], reverse=True)
        for g, idx in gaps:
            part1 = LineData(words=words[:idx+1]); part2 = LineData(words=words[idx+1:])
            if ContextLine.analyze(part1, 0, self.decimal_separator).price_ranges and ContextLine.analyze(part2, 0, self.decimal_separator).price_ranges: return [part1, part2]
        return None

    def _clean_name(self, text):
        return " ".join(text.split()).strip(".,-+* ")

    def _split_multiple_patterns(self, line_data: LineData) -> list[LineData] | None:
        """
        Усиленный поиск нескольких математических паттернов или просто нескольких цен в одной строке.
        """
        text = line_data.get_text()
        words = sorted(line_data.words, key=lambda w: w.x_left)
        
        # Находим все числа, похожие на цены
        price_matches = list(re.finditer(rf'(\d+[{re.escape(self.decimal_separator)}]\d{{2}})', text))
        if len(price_matches) < 2: return None

        print(f"DEBUG: Checking Siamese split for: {text}")
        print(f"DEBUG: Found {len(price_matches)} price matches")

        split_index = -1
        
        # 1. Поиск математических пар: Price * Qty = Total
        for i in range(len(price_matches)):
            for j in range(i + 1, len(price_matches)):
                try:
                    p1_val = float(price_matches[i].group(1).replace(self.decimal_separator, "."))
                    p2_val = float(price_matches[j].group(1).replace(self.decimal_separator, "."))
                    
                    # Ищем Qty между ними или рядом (в радиусе 30 символов)
                    start_search = price_matches[i].end()
                    end_search = price_matches[j].start()
                    sub_text = text[max(0, start_search-10):min(len(text), end_search+10)]
                    
                    qty_match = re.search(r'[xX×х]\s*(\d+[.,]?\d*)', sub_text)
                    if qty_match:
                        qty = float(qty_match.group(1).replace(",", "."))
                        print(f"DEBUG: Potential match: {p1_val} * {qty} = {p2_val}?")
                        if abs(round(p1_val * qty, 2) - p2_val) < 0.15:
                            print(f"DEBUG: Match found! Splitting after p2")
                            # Нашли пару! Ищем слово, соответствующее p2_val
                            p2_text = price_matches[j].group(1)
                            for k, w in enumerate(words):
                                if p2_text in w.text:
                                    split_index = k
                                    break
                            if split_index != -1: break
                except: continue
            if split_index != -1: break
        
        # 2. Если мат. пар нет, ищем просто большой зазор между словами
        if split_index == -1:
            max_gap = 0
            for i in range(len(words) - 1):
                gap = words[i+1].x_left - words[i].x_right
                if gap > max_gap:
                    max_gap = gap
                    split_index = i
            
            print(f"DEBUG: Max gap found: {max_gap} px at word {split_index}")
            # Разрезаем только если зазор действительно большой (минимум 40 пикселей)
            if max_gap < 30: # Уменьшим до 30
                split_index = -1

        if split_index != -1 and split_index < len(words) - 1:
            print(f"DEBUG: Splitting line at word index {split_index}")
            p1 = LineData(words=words[:split_index+1])
            p2 = LineData(words=words[split_index+1:])
            return [p1, p2]

        return None

    def _pre_pass_split_lines(self, lines):
        proc = []; mapping = {}
        for idx, line in enumerate(lines):
            ctx = ContextLine.analyze(line, 0, self.decimal_separator)
            if ctx.price_ranges and len(ctx.price_ranges) > 1:
                splits = self._split_line_smart(line, ctx)
                for s in splits: mapping[len(proc)] = idx; proc.append(s)
            else: mapping[len(proc)] = idx; proc.append(line)
        return proc, mapping

    def _split_line_smart(self, line, ctx):
        if ctx.is_full_item: return [line]
        res = self._split_multiple_patterns(line)
        if res: return res
        res = self._split_line_by_layers(line)
        if res: return res
        res = self._split_line_by_columns(line, ctx)
        if res: return res
        return [line]

    def _create_item(self, line, name, price, qty, total, line_indices, discount=0.0):
        name_clean = self._clean_name(name)
        total_keywords = ["zu zahlen", "summe", "total", "gesamt", "итого", "сумма", "betrag", "karte", "kundenbeleg", "ta nr", "brutto", "netto", "mwst"]
        if any(k in name_clean.lower() for k in total_keywords) or not any(c.isalpha() for c in name_clean): return None
        name_clean = re.split(rf"\s+\d+[{re.escape(self.decimal_separator)}]\d{{2}}", name_clean)[0].strip()
        if len(name_clean) < 10:
            words = [w for w in name_clean.split() if w not in ['&', 'A', 'B']]
            if len(words) <= 3 and all(len(w) < 5 for w in words) and not (price and total and price > 0 and total > 0):
                if not any(m in name_clean.lower() for m in ['pfand', 'cola', 'em']): return None
        return {
            "name": name_clean, "price": f"{price:.2f}" if price is not None else "0.00",
            "qty": str(int(qty)) if qty == int(qty) else str(qty),
            "total": f"{total:.2f}" if total is not None else "0.00",
            "discount": f"{discount:.2f}" if discount != 0 else "0.00",
            "tax": line.tax_code or "", "type": "contextual", "line_number": line.original_index + 1, "line": line.text[:80], "line_indices": line_indices,
        }
