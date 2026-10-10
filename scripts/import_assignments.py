"""一次性导入 scripts/人员.xlsx → operator_assignments 表（内勤负责关系）

Excel 结构（Sheet1，三列，内勤列有合并单元格，**没有表头行**——第 1 行就是数据）：
    内勤 | 保司 | 客服（顿号分隔，或「全部」）

规则：
    - 合并单元格向下填充（空的内勤格继承上一行）
    - 「全部」→ 写一行 user_id=NULL（该保司下全部客服）
    - 可重复跑：先清空表再全量写入（幂等）
    - 名字对不上 users 表 / 角色不符 / 保司不在下拉选项表 → 列出来退出，
      人工处理（建用户/改 Excel/补选项）后重跑

用法：
    python scripts/import_assignments.py          # 校验 + 写入
    python scripts/import_assignments.py --check  # 只校验不写入
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cit_api.model.model import DropdownOption, OperatorAssignment, User

# ── 数据库连接（与 init_users.py 一致，按需修改）──
DB_URL = "mysql+pymysql://root:1234@localhost:3306/insurance_work"
XLSX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "人员.xlsx")

OPERATOR_ROLES = (2, 22)   # 内勤 / 内勤主管
CS_ROLES = (1, 11)         # 客服 / 客服主管


def read_rows():
    """Excel → [(内勤名, 保司, 客服名或'全部'), ...]，内勤列向下填充。
    从第 1 行读起：这个文件没有表头，第 1 行就是梁晓红的数据。
    （若以后有人加了表头，第一行会生成「内勤/客服」这样的假名字，校验环节响亮报错，不会脏写。）"""
    ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[0]
    out, cur_op = [], None
    for r in ws.iter_rows(values_only=True):
        op, co, cs = (tuple(r) + (None, None, None))[:3]
        if op and str(op).strip():
            cur_op = str(op).strip()
        if not cur_op or not co or not cs:
            continue
        co = str(co).strip()
        for name in str(cs).replace("，", "、").replace(",", "、").split("、"):
            name = name.strip()
            if name:
                out.append((cur_op, co, name))
    # 去重（同一个人在同一张表里出现两次）
    return sorted(set(out))


def main():
    check_only = "--check" in sys.argv
    rows = read_rows()
    if not rows:
        print("Excel 里没读到数据，检查一下文件/列结构")
        sys.exit(1)

    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    users = session.query(User).all()
    by_name = {u.display_name: u for u in users}

    # ── 校验：内勤/客服名字都要在 users 表里且角色相符 ──
    errors = []
    # 保司必须在下拉选项表里：任务的保司也来自这张表，不在里面 = 永远匹配不到任务的死组
    known_cos = {o.value for o in session.query(DropdownOption)
                 .filter(DropdownOption.category == "insurance_company").all()}
    for co in sorted({r[1] for r in rows}):
        if co not in known_cos:
            errors.append(f"保司「{co}」不在下拉选项表（insurance_company），配了也匹配不到任务；"
                          f"改 Excel 用正式名，或先去 index「下拉选项管理」补上")
    for op in sorted({r[0] for r in rows}):
        u = by_name.get(op)
        if not u:
            errors.append(f"内勤「{op}」不在 users 表")
        elif u.role not in OPERATOR_ROLES:
            errors.append(f"内勤「{op}」角色不符（role={u.role}，需要 2/22）")
    for op, co, name in rows:
        if name == "全部":
            continue
        u = by_name.get(name)
        if not u:
            errors.append(f"客服「{name}」不在 users 表（{op} / {co}）")
        elif u.role not in CS_ROLES:
            errors.append(f"客服「{name}」角色不符（role={u.role}，需要 1/11）")
    if errors:
        print(f"有 {len(errors)} 个问题，未写入。处理（建用户/改 Excel）后重跑：")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    print(f"校验通过：{len({r[0] for r in rows})} 位内勤、{len({(r[0], r[1]) for r in rows})} 组关系、{len(rows)} 行")
    if check_only:
        print("--check：只校验，不写入")
        return

    # ── 写入：先清后写（幂等）──
    session.query(OperatorAssignment).delete(synchronize_session=False)
    for op, co, name in rows:
        ou = by_name[op]
        if name == "全部":
            session.add(OperatorAssignment(operator_id=ou.id, operator_name=ou.display_name,
                                           insurance_company=co, user_id=None, user_name=None))
        else:
            cu = by_name[name]
            session.add(OperatorAssignment(operator_id=ou.id, operator_name=ou.display_name,
                                           insurance_company=co, user_id=cu.id, user_name=cu.display_name))
    session.commit()
    print(f"已写入 {len(rows)} 行（表已清空重写）")


if __name__ == "__main__":
    main()
