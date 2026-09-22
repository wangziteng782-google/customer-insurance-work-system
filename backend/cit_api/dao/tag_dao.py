from sqlalchemy.orm import Session

from cit_api.model.model import Tag, TaskTag


class TagDAO:
    """标签数据访问层"""

    @staticmethod
    def list_by_user(db: Session, user_id: int) -> list[Tag]:
        return db.query(Tag).filter(Tag.user_id == user_id).order_by(Tag.created_at).all()

    @staticmethod
    def get(db: Session, tag_id: int, user_id: int) -> Tag | None:
        return db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == user_id).first()

    @staticmethod
    def get_by_name(db: Session, user_id: int, name: str) -> Tag | None:
        return db.query(Tag).filter(Tag.user_id == user_id, Tag.name == name).first()

    @staticmethod
    def create(db: Session, user_id: int, name: str, color: str) -> Tag:
        tag = Tag(user_id=user_id, name=name, color=color)
        db.add(tag)
        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def update(db: Session, tag_id: int, user_id: int, name: str, color: str | None) -> Tag | None:
        tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == user_id).first()
        if tag:
            if name:
                tag.name = name
            if color:
                tag.color = color
            db.commit()
            db.refresh(tag)
        return tag

    @staticmethod
    def delete(db: Session, tag_id: int, user_id: int) -> Tag | None:
        tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == user_id).first()
        if tag:
            # 级联清掉该用户所有任务上的此标签绑定，避免留脏数据
            db.query(TaskTag).filter(
                TaskTag.tag_id == tag_id, TaskTag.user_id == user_id
            ).delete(synchronize_session=False)
            db.delete(tag)
            db.commit()
        return tag

    @staticmethod
    def list_task_tags(db: Session, user_id: int, task_id: str) -> list[TaskTag]:
        return db.query(TaskTag).filter(
            TaskTag.user_id == user_id, TaskTag.task_id == task_id
        ).all()

    @staticmethod
    def list_bindings(db: Session, user_id: int) -> list:
        """当前用户全部任务标签绑定（JOIN 标签名和颜色），列表页一次拉全避免逐任务请求"""
        return (
            db.query(TaskTag.id, TaskTag.task_id, Tag.id, Tag.name, Tag.color)
            .join(Tag, Tag.id == TaskTag.tag_id)
            .filter(TaskTag.user_id == user_id)
            .all()
        )

    @staticmethod
    def add_task_tag(db: Session, user_id: int, task_id: str, tag_id: int) -> TaskTag:
        tt = TaskTag(user_id=user_id, task_id=task_id, tag_id=tag_id)
        db.add(tt)
        db.commit()
        db.refresh(tt)
        return tt

    @staticmethod
    def delete_task_tag(db: Session, user_id: int, task_id: str, tt_id: int) -> TaskTag | None:
        tt = db.query(TaskTag).filter(
            TaskTag.id == tt_id, TaskTag.user_id == user_id, TaskTag.task_id == task_id
        ).first()
        if tt:
            db.delete(tt)
            db.commit()
        return tt
