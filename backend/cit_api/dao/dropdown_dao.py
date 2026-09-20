from sqlalchemy.orm import Session

from cit_api.model.model import DropdownOption


class DropdownDAO:
    """下拉选项数据访问层"""

    @staticmethod
    def list_by_category(db: Session, category: str) -> list[DropdownOption]:
        return (
            db.query(DropdownOption)
            .filter(DropdownOption.category == category)
            # 同 sort 时按 id 兜底，保证顺序稳定（新增项 sort=999 排最后）
            .order_by(DropdownOption.sort, DropdownOption.id)
            .all()
        )

    @staticmethod
    def get_by_value(db: Session, category: str, value: str) -> DropdownOption | None:
        return db.query(DropdownOption).filter_by(category=category, value=value).first()

    @staticmethod
    def add(db: Session, category: str, value: str) -> DropdownOption:
        opt = DropdownOption(category=category, value=value, sort=999)
        db.add(opt)
        db.commit()
        db.refresh(opt)
        return opt

    @staticmethod
    def delete(db: Session, category: str, opt_id: int) -> DropdownOption | None:
        opt = db.query(DropdownOption).filter_by(id=opt_id, category=category).first()
        if opt:
            db.delete(opt)
            db.commit()
        return opt
