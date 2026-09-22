from fastapi import HTTPException
from sqlalchemy.orm import Session

from cit_api.dao.tag_dao import TagDAO


class TagService:
    """标签业务逻辑层"""

    def __init__(self, db: Session):
        self.db = db

    def list_tags(self, user_id: int) -> list[dict]:
        tags = TagDAO.list_by_user(self.db, user_id)
        return [{"id": t.id, "name": t.name, "color": t.color} for t in tags]

    def create_tag(self, user_id: int, name: str, color: str) -> dict:
        name = (name or "").strip()
        if not name:
            raise HTTPException(400, "标签名不能为空")
        if len(name) > 30:
            raise HTTPException(400, "标签名最长30字符")
        if TagDAO.get_by_name(self.db, user_id, name):
            raise HTTPException(409, "标签名已存在")
        tag = TagDAO.create(self.db, user_id, name, color or "#1677ff")
        return {"id": tag.id, "name": tag.name, "color": tag.color}

    def rename_tag(self, user_id: int, tag_id: int, name: str, color: str | None = None) -> dict:
        """改名/改色：task_tags 只存引用，改 tags 一处全部任务卡片自动生效"""
        name = (name or "").strip()
        if not name:
            raise HTTPException(400, "标签名不能为空")
        if len(name) > 30:
            raise HTTPException(400, "标签名最长30字符")
        if not TagDAO.get(self.db, tag_id, user_id):
            raise HTTPException(404, "标签不存在")
        dup = TagDAO.get_by_name(self.db, user_id, name)
        if dup and dup.id != tag_id:
            raise HTTPException(409, "标签名已存在")
        tag = TagDAO.update(self.db, tag_id, user_id, name, color)
        return {"id": tag.id, "name": tag.name, "color": tag.color}

    def delete_tag(self, user_id: int, tag_id: int) -> dict:
        tag = TagDAO.delete(self.db, tag_id, user_id)
        if not tag:
            raise HTTPException(404, "标签不存在")
        return {"msg": "已删除"}

    def list_task_tags(self, user_id: int, task_id: str) -> list[dict]:
        tts = TagDAO.list_task_tags(self.db, user_id, task_id)
        result = []
        for tt in tts:
            tag = TagDAO.get(self.db, tt.tag_id, user_id)
            if tag:
                result.append({"id": tt.id, "tag_id": tag.id, "name": tag.name, "color": tag.color})
        return result

    def list_bindings(self, user_id: int) -> list[dict]:
        return [
            {"tt_id": r[0], "task_id": r[1], "tag_id": r[2], "name": r[3], "color": r[4]}
            for r in TagDAO.list_bindings(self.db, user_id)
        ]

    def add_task_tag(self, user_id: int, task_id: str, tag_id: int) -> dict:
        tag = TagDAO.get(self.db, tag_id, user_id)
        if not tag:
            raise HTTPException(404, "标签不存在")
        existing = TagDAO.list_task_tags(self.db, user_id, task_id)
        if any(tt.tag_id == tag_id for tt in existing):
            raise HTTPException(409, "该任务已添加此标签")
        tt = TagDAO.add_task_tag(self.db, user_id, task_id, tag_id)
        return {"id": tt.id, "tag_id": tag.id, "name": tag.name, "color": tag.color}

    def delete_task_tag(self, user_id: int, task_id: str, tt_id: int) -> dict:
        tt = TagDAO.delete_task_tag(self.db, user_id, task_id, tt_id)
        if not tt:
            raise HTTPException(404, "关联不存在")
        return {"msg": "已删除"}
