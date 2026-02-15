"""
邮件模板服务
提供模板的 CRUD 操作和变量替换功能
"""
import re
from functools import lru_cache
from typing import Optional

from app.log import logger
from app.models.exchange import ExchangeEmailTemplate
from app.schemas.exchange import TemplateCreate, TemplateUpdate


class TemplateService:
    """
    模板服务
    管理邮件模板，支持变量替换
    """
    
    
    def __init__(self):
        # 初始化 Jinja2 环境
        from jinja2 import Environment, BaseLoader, select_autoescape
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(['html', 'xml']),
            variable_start_string='{{',
            variable_end_string='}}',
        )
    
    async def create_template(self, data: TemplateCreate, owner_id: int) -> dict:
        """
        创建邮件模板
        """
        try:
            # 自动提取变量
            variables = data.variables
            if not variables:
                # 使用 Jinja2 meta 提取变量
                from jinja2 import meta
                env = self.env
                ast = env.parse(f"{data.subject} {data.body}")
                variables = list(meta.find_undeclared_variables(ast))
            
            template = await ExchangeEmailTemplate.create(
                name=data.name,
                subject=data.subject,
                body=data.body,
                body_type=data.body_type,
                category=data.category,
                variables=variables,
                remark=data.remark,
                owner_id=owner_id,
            )
            
            logger.info(f"创建模板成功: {template.name}")
            return {
                "success": True,
                "message": "模板创建成功",
                "data": await self._template_to_dict(template),
            }
            
        except Exception as e:
            logger.error(f"创建模板失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}
    
    async def update_template(self, data: TemplateUpdate, owner_id: int) -> dict:
        """
        更新邮件模板
        """
        try:
            template = await ExchangeEmailTemplate.filter(
                id=data.id, 
                owner_id=owner_id
            ).first()
            
            if not template:
                return {"success": False, "message": "模板不存在或无权访问"}
            
            # 更新字段
            update_fields = {}
            if data.name is not None:
                update_fields["name"] = data.name
            if data.subject is not None:
                update_fields["subject"] = data.subject
            if data.body is not None:
                update_fields["body"] = data.body
            if data.body_type is not None:
                update_fields["body_type"] = data.body_type
            if data.category is not None:
                update_fields["category"] = data.category
            if data.variables is not None:
                update_fields["variables"] = data.variables
            if data.is_active is not None:
                update_fields["is_active"] = data.is_active
            if data.remark is not None:
                update_fields["remark"] = data.remark
            
            if update_fields:
                await ExchangeEmailTemplate.filter(id=data.id).update(**update_fields)
                await template.refresh_from_db()
            
            logger.info(f"更新模板成功: {template.name}")
            return {
                "success": True,
                "message": "模板更新成功",
                "data": await self._template_to_dict(template),
            }
            
        except Exception as e:
            logger.error(f"更新模板失败: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}"}
    
    async def delete_template(self, template_id: int, owner_id: int) -> dict:
        """
        删除邮件模板
        """
        try:
            template = await ExchangeEmailTemplate.filter(
                id=template_id, 
                owner_id=owner_id
            ).first()
            
            if not template:
                return {"success": False, "message": "模板不存在或无权访问"}
            
            name = template.name
            await template.delete()
            
            logger.info(f"删除模板成功: {name}")
            return {"success": True, "message": "模板删除成功"}
            
        except Exception as e:
            logger.error(f"删除模板失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}
    
    async def list_templates(
        self, 
        owner_id: int, 
        page: int = 1, 
        page_size: int = 20,
        category: Optional[str] = None,
        active_only: bool = False,
    ) -> dict:
        """
        获取模板列表
        """
        try:
            query = ExchangeEmailTemplate.filter(owner_id=owner_id)
            
            if category:
                query = query.filter(category=category)
            if active_only:
                query = query.filter(is_active=True)
            
            total = await query.count()
            templates = await query.order_by("-created_at").offset(
                (page - 1) * page_size
            ).limit(page_size)
            
            items = [await self._template_to_dict(t) for t in templates]
            
            return {
                "success": True,
                "total": total,
                "items": items,
            }
            
        except Exception as e:
            logger.error(f"获取模板列表失败: {e}")
            return {"success": False, "message": f"获取失败: {str(e)}"}
    
    async def get_template(self, template_id: int, owner_id: int) -> dict:
        """
        获取单个模板
        """
        try:
            template = await ExchangeEmailTemplate.filter(
                id=template_id,
                owner_id=owner_id,
            ).first()
            
            if not template:
                return {"success": False, "message": "模板不存在"}
            
            return {
                "success": True,
                "data": await self._template_to_dict(template),
            }
            
        except Exception as e:
            logger.error(f"获取模板失败: {e}")
            return {"success": False, "message": f"获取失败: {str(e)}"}
    
    async def preview_template(
        self, 
        template_id: int, 
        owner_id: int,
        variables: dict[str, str],
    ) -> dict:
        """
        预览模板（替换变量后）
        """
        try:
            template = await ExchangeEmailTemplate.filter(
                id=template_id,
                owner_id=owner_id,
            ).first()
            
            if not template:
                return {"success": False, "message": "模板不存在"}
            
            # 替换变量
            subject = self._replace_variables(template.subject, variables)
            body = self._replace_variables(template.body, variables)
            
            return {
                "success": True,
                "data": {
                    "subject": subject,
                    "body": body,
                    "body_type": template.body_type,
                },
            }
            
        except Exception as e:
            logger.error(f"预览模板失败: {e}")
            return {"success": False, "message": f"预览失败: {str(e)}"}
    
    async def get_template_for_send(self, template_id: int) -> Optional[ExchangeEmailTemplate]:
        """
        获取用于发送的模板（API调用，不检查owner）
        """
        return await ExchangeEmailTemplate.filter(
            id=template_id,
            is_active=True,
        ).first()
    
    async def get_template_by_name(self, name: str) -> Optional[ExchangeEmailTemplate]:
        """
        按名称获取用于发送的模板（API调用，不检查owner）
        """
        return await ExchangeEmailTemplate.filter(
            name=name,
            is_active=True,
        ).first()
    
    def _replace_variables(self, text: str, variables: dict[str, str]) -> str:
        """
        使用 Jinja2 渲染模板
        """
        try:
            template = self.env.from_string(text)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            # Fallback or re-raise? Return original for now to avoid crash
            return text
    
    async def _template_to_dict(self, template: ExchangeEmailTemplate) -> dict:
        """
        将模板转换为字典
        """
        return {
            "id": template.id,
            "name": template.name,
            "subject": template.subject,
            "body": template.body,
            "body_type": template.body_type,
            "category": template.category,
            "variables": template.variables or [],
            "is_active": template.is_active,
            "remark": template.remark,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }


# 全局服务实例
_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """获取模板服务实例"""
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service
