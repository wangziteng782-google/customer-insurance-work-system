from sqlalchemy.orm import Session

from cit_api.model.model import OperatorAssignment


class AssignmentDAO:
    """内勤负责关系数据访问层"""

    @staticmethod
    def list_all(db: Session) -> list[OperatorAssignment]:
        return (
            db.query(OperatorAssignment)
            .order_by(OperatorAssignment.operator_id, OperatorAssignment.id)
            .all()
        )

    @staticmethod
    def replace_group(
        db: Session,
        operator_id: int,
        operator_name: str,
        insurance_company: str,
        members: list[tuple[int, str]] | None,
    ) -> list[OperatorAssignment]:
        """整组替换该（内勤, 保司）的行：删旧插新，一个事务。
        members 为 None = 该保司下全部客服（写一行 user_id=NULL）；
        否则为 [(客服ID, 客服姓名), ...]，姓名冗余只做显示。"""
        db.query(OperatorAssignment).filter(
            OperatorAssignment.operator_id == operator_id,
            OperatorAssignment.insurance_company == insurance_company,
        ).delete(synchronize_session=False)
        rows = (
            [OperatorAssignment(operator_id=operator_id, operator_name=operator_name,
                                insurance_company=insurance_company, user_id=None, user_name=None)]
            if members is None else
            [OperatorAssignment(operator_id=operator_id, operator_name=operator_name,
                                insurance_company=insurance_company, user_id=uid, user_name=uname)
             for uid, uname in members]
        )
        db.add_all(rows)
        db.commit()
        for r in rows:
            db.refresh(r)
        return rows

    @staticmethod
    def delete_group(db: Session, operator_id: int, insurance_company: str) -> int:
        deleted = db.query(OperatorAssignment).filter(
            OperatorAssignment.operator_id == operator_id,
            OperatorAssignment.insurance_company == insurance_company,
        ).delete(synchronize_session=False)
        db.commit()
        return deleted
