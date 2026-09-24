"""OCR 身份证识别服务 — 基于 PaddleOCR"""
import os
import re
import traceback

os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["KMP_AFFINITY"] = "disabled"

import paddlex.utils.deps as _px_deps
def _dummy_require_extra(extra, *, obj_name=None, alt=None):
    pass
def _dummy_require_deps(*deps, obj_name=None):
    pass
_px_deps.require_extra = _dummy_require_extra
_px_deps.require_deps = _dummy_require_deps

from paddleocr import PaddleOCR


def _resize_for_engine(image):
    """识别前的缩放（身份证照片 600px、其它 1200px）

    不只是提速：超大图直接喂给检测器会**一个框都出不来**，所以这一步是出框的前提。
    """
    from PIL import Image as PILImage
    import numpy as np

    if isinstance(image, PILImage.Image):
        image = np.array(image)
    if isinstance(image, np.ndarray):
        h, w = image.shape[:2]
        is_id_card = h > 1500 or w > 1500
        max_size = 600 if is_id_card else 1200
        min_size = 300
        if h > max_size or w > max_size:
            scale = max_size / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            if new_h < min_size or new_w < min_size:
                scale = min_size / min(h, w)
                new_h, new_w = int(h * scale), int(w * scale)
            image = np.array(PILImage.fromarray(image).resize((new_w, new_h), PILImage.LANCZOS))
    return image


class OCREngine:
    """PaddleOCR 封装"""

    def __init__(self, lang="ch"):
        self.lang = lang
        self.ocr = None
        self._initialized = False
        self._init_error = None

    def initialize(self):
        if self._initialized:
            return True
        try:
            self.ocr = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                lang=self.lang,
                engine="onnxruntime",
                det_db_box_thresh=0.1,
                det_db_unclip_ratio=1.0,
            )
            self._initialized = True
            return True
        except Exception as e:
            self._init_error = f"{type(e).__name__}: {e}"
            return False

    def recognize(self, image):
        """单张图片识别 -> (full_text, error)"""
        if not self._initialized:
            if not self.initialize():
                return "", self._init_error
        try:
            image = _resize_for_engine(image)
            result = self.ocr.predict(image)
            text_lines = []
            for page in result:
                texts = page.get("rec_texts", [])
                scores = page.get("rec_scores", [])
                # 坐标键名随 PaddleOCR 版本变：新版在 dt_polys / rec_polys，老版本才叫 det_boxes。
                # 读不到就等于"没有坐标" → 会退回按模型原始顺序一段一行、完全不做行合并，
                # 表格里同一行的姓名和号码就会被拆成两行（实际踩到的坑）
                boxes = (page.get("det_boxes") or page.get("dt_polys")
                         or page.get("rec_polys") or page.get("rec_boxes") or [])
                if boxes:
                    text_blocks = []
                    for i, (text, score, box) in enumerate(zip(texts, scores, boxes)):
                        text = str(text)
                        x_coords = [p[0] for p in box]
                        y_coords = [p[1] for p in box]
                        text_blocks.append({
                            "text": text, "score": score,
                            "left": min(x_coords), "right": max(x_coords),
                            "top": min(y_coords), "bottom": max(y_coords)
                        })
                    text_blocks.sort(key=lambda b: b["top"])
                    if text_blocks:
                        current_row = [text_blocks[0]]
                        for block in text_blocks[1:]:
                            # 同行判定：与「当前行整体」做垂直重叠，重叠超过较矮那个框的一半就算同一行。
                            # 不能用固定像素阈值（原来是"上一个框底边到下一个框顶边 > 15px"）：
                            # 图片会先缩到 600/1200px 再识别，此时字号只有 9~12px、相邻两行的
                            # 间隙常常不到 10px，固定 15px 会把上下两行并成一行；而表格里
                            # 姓名和号码字号不同、基线不同，同一个固定阈值又会把同一行拆成两行。
                            row_top = min(b["top"] for b in current_row)
                            row_bottom = max(b["bottom"] for b in current_row)
                            overlap = min(row_bottom, block["bottom"]) - max(row_top, block["top"])
                            shorter = min(row_bottom - row_top,
                                          block["bottom"] - block["top"]) or 1
                            if overlap >= shorter * 0.5:
                                current_row.append(block)
                            else:
                                current_row.sort(key=lambda b: b["left"])
                                text_lines.append(" ".join(b["text"] for b in current_row))
                                current_row = [block]
                        if current_row:
                            current_row.sort(key=lambda b: b["left"])
                            text_lines.append(" ".join(b["text"] for b in current_row))
                else:
                    text_lines.extend(str(t) for t in texts)
            return "\n".join(text_lines), None
        except Exception as e:
            return "", f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


# ── 身份证信息提取 ──

_ID_NUMBER_PATTERN = re.compile(r'(?<!\d)\d{17}[\dXx](?!\d)')
_SCI_NUMBER_PATTERN = re.compile(r'(\d+\.?\d*)[Ee]\+?(\d+)')


def _expand_scientific_notation(text):
    """科学计数法还原"""
    def _replace(match):
        coef_str = match.group(1)
        exp = int(match.group(2))
        digits = coef_str.replace('.', '')
        dot_pos = coef_str.find('.')
        if dot_pos < 0:
            dot_pos = len(digits)
        new_dot = dot_pos + exp
        if new_dot >= len(digits):
            full = digits + '0' * (new_dot - len(digits))
        else:
            full = digits[:new_dot] + digits[new_dot:]
        if len(full) == 18:
            return full
        return match.group(0)
    return _SCI_NUMBER_PATTERN.sub(_replace, text)


_NAME_PATTERN = re.compile(r'姓名[\s　:：\n\r]*(\S{2,4})')
_NAME_FALLBACK_PATTERN = re.compile(r'([一-鿿]{2,4})')

_ADDRESS_KEYWORDS = set('镇村省市县区乡号路街道组栋楼室弄巷坊屯')

_ID_NOISE_VALUES = {
    '性别男', '性别女', '别男', '别女',
    '民族汉', '族汉',
    '出生年月',
    '公民身份',
    '签发机关',
    '有效期限',
    '姓名',
    '居民身份证',
}


def _is_valid_name(candidate):
    if not candidate or len(candidate) < 2 or len(candidate) > 4:
        return False
    if not all('一' <= ch <= '鿿' for ch in candidate):
        return False
    if candidate in _ID_NOISE_VALUES:
        return False
    if any(kw in candidate for kw in ('姓名', '性别', '民族', '出生', '签发', '期限', '公民', '身份证', '居民')):
        return False
    # ponytail: 地址字黑名单式过滤，专治"住址续行被当成姓名"（河北省邯郸市邱县 → 河北省邯）
    # 取舍：姓名本身含地址字（如"路遥"）会被留空，交给内勤手填——宁可漏，不可误收
    # 天花板：若出现不含地址字的误判（如公司名），再引入 address_text 交集判断
    if any(kw in candidate for kw in _ADDRESS_KEYWORDS):
        return False
    return True


def extract_id_info(text):
    """从 OCR 文本提取 (姓名, 身份证号)"""
    if not text:
        return "", ""
    text = _expand_scientific_notation(text)
    id_match = _ID_NUMBER_PATTERN.search(text)
    id_number = id_match.group(0) if id_match else ""
    name = ""
    name_match = _NAME_PATTERN.search(text)
    if name_match:
        candidate = name_match.group(1)
        chinese_parts = re.findall(r'[一-鿿]+', candidate)
        for part in chinese_parts:
            part = part[:4]
            if _is_valid_name(part):
                name = part
                break
    if not name:
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if id_number and id_number in line:
                continue
            if any(kw in line for kw in ['出生', '住址', '民族', '公民', '签发', '期限', '号码', '身份证', '居民', '性别']):
                continue
            fb_match = _NAME_FALLBACK_PATTERN.search(line)
            if fb_match:
                candidate = fb_match.group(1)
                if _is_valid_name(candidate):
                    name = candidate
                    break
    return name, id_number


# ── 身份证校验 ──

CHECK_CODES = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
WEIGHT_FACTORS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]

AREA_CODES = {
    '110000': '北京市', '120000': '天津市', '130000': '河北省',
    '140000': '山西省', '150000': '内蒙古自治区', '210000': '辽宁省',
    '220000': '吉林省', '230000': '黑龙江省', '310000': '上海市',
    '320000': '江苏省', '330000': '浙江省', '340000': '安徽省',
    '350000': '福建省', '360000': '江西省', '370000': '山东省',
    '410000': '河南省', '420000': '湖北省', '430000': '湖南省',
    '440000': '广东省', '450000': '广西壮族自治区', '460000': '海南省',
    '500000': '重庆市', '510000': '四川省', '520000': '贵州省',
    '530000': '云南省', '540000': '西藏自治区', '610000': '陕西省',
    '620000': '甘肃省', '630000': '青海省', '640000': '宁夏回族自治区',
    '650000': '新疆维吾尔自治区', '710000': '台湾省',
    '810000': '香港特别行政区', '820000': '澳门特别行政区',
}


def validate_check_code(id_number: str) -> bool:
    """ISO 7064 MOD 11-2 校验码验证"""
    if len(id_number) != 18:
        return False
    total = 0
    for i in range(17):
        total += int(id_number[i]) * WEIGHT_FACTORS[i]
    return CHECK_CODES[total % 11] == id_number[17].upper()


def extract_birth_date(id_number: str):
    """提取出生日期"""
    if len(id_number) != 18:
        return None
    try:
        year = int(id_number[6:10])
        month = int(id_number[10:12])
        day = int(id_number[12:14])
        import datetime
        datetime.date(year, month, day)
        if year < 1900 or datetime.date(year, month, day) > datetime.date.today():
            return None
        return f"{year}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        return None


def extract_gender(id_number: str):
    """提取性别"""
    if len(id_number) != 18:
        return None
    return "男" if int(id_number[16]) % 2 == 1 else "女"


def calculate_age(birth_date: str):
    """计算年龄"""
    if not birth_date:
        return None
    import datetime
    try:
        d = datetime.date.fromisoformat(birth_date)
        today = datetime.date.today()
        age = today.year - d.year
        if (today.month, today.day) < (d.month, d.day):
            age -= 1
        return age
    except (ValueError, TypeError):
        return None


def get_area_info(id_number: str):
    """地区码查表"""
    if len(id_number) != 18:
        return None
    code = id_number[:6]
    for prefix in [code[:4] + '00', code[:2] + '0000']:
        if prefix in AREA_CODES:
            return AREA_CODES[prefix]
    return None


# ── 身份证校验器（完全复刻 Umi-OCR） ──

import datetime as _dt


class IDCardValidator:
    """身份证校验器 — 逻辑与 Umi-OCR id_card_validator.py 完全一致"""

    CHECK_CODES = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
    WEIGHT_FACTORS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]

    AREA_CODES = {
        '110000': '北京市', '110101': '北京市东城区', '110102': '北京市西城区',
        '120000': '天津市', '130000': '河北省', '130400': '河北省邯郸市',
        '130431': '河北省邯郸市邱县', '140000': '山西省', '150000': '内蒙古自治区',
        '210000': '辽宁省', '220000': '吉林省', '230000': '黑龙江省',
        '310000': '上海市', '320000': '江苏省', '330000': '浙江省',
        '340000': '安徽省', '350000': '福建省', '360000': '江西省',
        '370000': '山东省', '410000': '河南省', '420000': '湖北省',
        '430000': '湖南省', '440000': '广东省', '450000': '广西壮族自治区',
        '460000': '海南省', '500000': '重庆市', '510000': '四川省',
        '520000': '贵州省', '530000': '云南省', '540000': '西藏自治区',
        '610000': '陕西省', '620000': '甘肃省', '630000': '青海省',
        '640000': '宁夏回族自治区', '650000': '新疆维吾尔自治区',
        '710000': '台湾省', '810000': '香港特别行政区', '820000': '澳门特别行政区',
    }

    @classmethod
    def extract_id_from_text(cls, text):
        text = text.strip()
        match = re.search(r'([一-龥]{2,4})[^\d]*?(\d{17}[\dXx])', text)
        if match:
            return match.group(1), match.group(2).upper()
        id_match = re.search(r'\b\d{17}[\dXx]\b', text)
        if id_match:
            return None, id_match.group().upper()
        return None, None

    @classmethod
    def calc_correct_check_code(cls, id_17):
        try:
            total = sum(int(id_17[i]) * cls.WEIGHT_FACTORS[i] for i in range(17))
            return cls.CHECK_CODES[total % 11]
        except (ValueError, IndexError):
            return '?'

    @classmethod
    def validate_check_code(cls, id_card):
        if len(id_card) != 18:
            return False
        try:
            return id_card[17].upper() == cls.calc_correct_check_code(id_card[:17])
        except (ValueError, IndexError):
            return False

    @classmethod
    def validate_birth_date(cls, id_card):
        if len(id_card) != 18:
            return False, None, None
        try:
            date_str = id_card[6:14]
            year, month, day = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
            birth = _dt.date(year, month, day)
            formatted = f"{year:04d}-{month:02d}-{day:02d}"
            if birth > _dt.date.today() or birth.year < 1900:
                return False, date_str, formatted
            return True, date_str, formatted
        except ValueError:
            return False, None, None

    @classmethod
    def extract_gender(cls, id_card):
        if len(id_card) != 18:
            return None
        try:
            return '男' if int(id_card[16]) % 2 == 1 else '女'
        except (ValueError, IndexError):
            return None

    @classmethod
    def calculate_age(cls, birth_date_str):
        try:
            birth = _dt.datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            today = _dt.date.today()
            age = today.year - birth.year
            if (today.month, today.day) < (birth.month, birth.day):
                age -= 1
            return age
        except (ValueError, TypeError):
            return None

    @classmethod
    def get_area_info(cls, id_card):
        if len(id_card) < 6:
            return None
        return cls.AREA_CODES.get(id_card[:6])

    @classmethod
    def validate_id_type(cls, id_card):
        if re.match(r'^\d{17}[\dXx]$', id_card):
            return '身份证'
        elif re.match(r'^[A-Za-z]\d{7,9}$', id_card):
            return '护照'
        elif re.match(r'^[A-Za-z]{2}\d{10}$', id_card):
            return '港澳台通行证'
        return '其他'

    @classmethod
    def validate(cls, input_text):
        result = {
            'name': None, 'id_card': None, 'id_type': None,
            'area': None, 'birth_date': None, 'age': None, 'gender': None,
            'correct_check_code': None, 'is_valid': False,
            'warnings': [], 'errors': [],
        }
        name, id_card = cls.extract_id_from_text(input_text)
        result['name'] = name
        result['id_card'] = id_card

        if not id_card:
            result['errors'].append('无法识别身份证号码，请检查输入格式')
            return result

        result['id_type'] = cls.validate_id_type(id_card)

        if len(id_card) != 18:
            result['errors'].append(f'身份证号码长度错误：应为18位，实际为{len(id_card)}位')
            return result

        if not id_card[:17].isdigit():
            result['errors'].append('身份证号前17位必须全部为数字')
            return result

        last_char = id_card[17].upper()
        if not (last_char.isdigit() or last_char == 'X'):
            result['errors'].append('身份证号最后一位必须是数字或X')
            return result

        result['area'] = cls.get_area_info(id_card)

        is_date_valid, birth_num, birth_fmt = cls.validate_birth_date(id_card)
        result['birth_date'] = birth_fmt if birth_fmt else birth_num
        if not is_date_valid:
            result['errors'].append(f'身份证出生日期无效：{birth_num}，请检查第7-14位')
            return result

        age = cls.calculate_age(birth_fmt)
        result['age'] = age
        if age is not None:
            if age < 0:
                result['errors'].append('出生日期在未来，不可能出现负年龄')
            elif age < 18:
                result['warnings'].append(f'未满18周岁，年龄为{age}岁')
            elif age > 100:
                result['warnings'].append(f'年龄过大（{age}岁），请核对出生日期')

        result['gender'] = cls.extract_gender(id_card)

        is_check_valid = cls.validate_check_code(id_card)
        if not is_check_valid:
            result['correct_check_code'] = cls.calc_correct_check_code(id_card[:17])
            result['errors'].append(
                f'身份证校验码错误！当前最后一位：{last_char}，正确最后一位应为：{result["correct_check_code"]}'
            )

        result['is_valid'] = (is_check_valid and is_date_valid and len(result['errors']) == 0)
        return result


def verify_id_card(name, id_number):
    """对单条姓名+身份证号执行 Umi-OCR 风格的完整校验"""
    input_text = f"{name} {id_number}".strip() if name else (id_number or '')
    return IDCardValidator.validate(input_text)


# ── 全局引擎实例 ──

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = OCREngine()
    return _engine


# 七牛图片处理：识别不需要原图，1600 长边足够（PaddleOCR 内部还会再缩放）
# auto-orient 必须带：七牛处理完会丢掉 EXIF 方向，不先转正，手机竖拍的照片是躺着的，识别率会掉
# 实测 11MB 原图 → 0.5MB，下载 4.5s → ~1s（也顺带解决了 timeout=10 容易超时失败的问题）
_OCR_IMG_FOP = "imageMogr2/auto-orient/thumbnail/1600x>"


def _fetch_for_ocr(image_url: str) -> bytes:
    """取识别用的图片字节：优先七牛处理后的 1600 版本，不可用则回退原图"""
    import requests as _req

    sep = "&" if "?" in image_url else "?"
    try:
        resp = _req.get(image_url + sep + _OCR_IMG_FOP, timeout=20)
        if resp.status_code == 200 and resp.content:
            return resp.content
    except Exception:
        pass  # 桶没开图片处理 / 网络抖动 → 走原图
    resp = _req.get(image_url, timeout=30)
    resp.raise_for_status()
    return resp.content


def _load_ocr_image(image_url: str):
    """下载并解码图片（EXIF 转正 + 转 RGB），身份证识别 / 原样识别共用"""
    from PIL import Image as PILImage, ImageOps

    image = PILImage.open(__import__('io').BytesIO(_fetch_for_ocr(image_url)))
    # 原图可能带 EXIF 方向（手机竖拍），PIL 不会自动转正
    image = ImageOps.exif_transpose(image)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    return image


def recognize_id_card(image_url: str):
    """下载图片并识别身份证 — 主入口"""
    full_text, error = get_engine().recognize(_load_ocr_image(image_url))
    if error:
        return None, error

    name, id_number = extract_id_info(full_text)
    if not id_number:
        return None, "未识别到身份证号"

    valid = validate_check_code(id_number)
    birth_date = extract_birth_date(id_number)
    return {
        "name": name,
        "id_number": id_number,
        "valid": valid,
        "birth_date": birth_date,
        "gender": extract_gender(id_number),
        "age": calculate_age(birth_date),
        "area": get_area_info(id_number),
    }, None


def recognize_raw(image_url: str):
    """下载图片并原样输出 OCR 全文（不做身份证字段提取）

    对应「图片识别」按钮：截图 / 证照等任意图片，把 OCR 认到的文字按阅读顺序原样返回，
    让内勤自己核对、复制。与 recognize_id_card 只差最后一步不做字段提取。
    """
    full_text, error = get_engine().recognize(_load_ocr_image(image_url))
    if error:
        return None, error
    if not full_text.strip():
        return None, "未识别到文字"
    return {"text": full_text}, None


# ── 自检：只验证姓名/身份证号提取规则，不需要 OCR 引擎 ──
# 运行：cd backend && python -m cit_api.service.ocr_service

if __name__ == "__main__":
    _CARD = ("姓名 王五\n性别 男 民族 汉\n出生 2003年1月22日\n"
             "住址 河北省邯郸市邱县\n公民身份号码 13043120030122123X")
    assert extract_id_info(_CARD) == ("王五", "13043120030122123X")
    # 姓名与标签粘连
    assert extract_id_info("姓名张三\n13043120030122123X") == ("张三", "13043120030122123X")
    # 回归：住址续行不得被当成姓名（修复前会得到 "河北省邯"）
    assert extract_id_info("住址\n河北省邯郸市邱县\n13043120030122123X")[0] == ""
    # 无姓名 → 留空，只保留号码
    assert extract_id_info("13043120030122123X")[0] == ""
    # 科学计数法还原后的号码仍要提取到
    assert extract_id_info("号码 1.30431200301221E+17")[1] == "130431200301221000"
    print("extract_id_info self-check passed")
