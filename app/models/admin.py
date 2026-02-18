from tortoise import fields

from app.schemas.menus import MenuType

from .base import BaseModel, TimestampMixin
from .enums import MethodType


class User(BaseModel, TimestampMixin):
    username = fields.CharField(max_length=20, unique=True, description="用户名称", db_index=True)
    alias = fields.CharField(max_length=30, null=True, description="姓名", db_index=True)
    email = fields.CharField(max_length=255, unique=True, description="邮箱", db_index=True)
    phone = fields.CharField(max_length=20, null=True, description="电话", db_index=True)
    password = fields.CharField(max_length=128, null=True, description="密码")
    is_active = fields.BooleanField(default=True, description="是否激活", db_index=True)
    is_superuser = fields.BooleanField(default=False, description="是否为超级管理员", db_index=True)
    last_login = fields.DatetimeField(null=True, description="最后登录时间", db_index=True)
    roles = fields.ManyToManyField("models.Role", related_name="user_roles")
    dept_id = fields.IntField(null=True, description="部门ID", db_index=True)

    class Meta:
        table = "user"


class Role(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, unique=True, description="角色名称", db_index=True)
    desc = fields.CharField(max_length=500, null=True, description="角色描述")
    menus = fields.ManyToManyField("models.Menu", related_name="role_menus")
    apis = fields.ManyToManyField("models.Api", related_name="role_apis")

    class Meta:
        table = "role"


class Api(BaseModel, TimestampMixin):
    path = fields.CharField(max_length=100, description="API路径", db_index=True)
    method = fields.CharEnumField(MethodType, description="请求方法", db_index=True)
    summary = fields.CharField(max_length=500, description="请求简介", db_index=True)
    tags = fields.CharField(max_length=100, description="API标签", db_index=True)

    class Meta:
        table = "api"


class Menu(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, description="菜单名称", db_index=True)
    remark = fields.JSONField(null=True, description="保留字段")
    menu_type = fields.CharEnumField(MenuType, null=True, description="菜单类型")
    icon = fields.CharField(max_length=100, null=True, description="菜单图标")
    path = fields.CharField(max_length=100, description="菜单路径", db_index=True)
    order = fields.IntField(default=0, description="排序", db_index=True)
    parent_id = fields.IntField(default=0, description="父菜单ID", db_index=True)
    is_hidden = fields.BooleanField(default=False, description="是否隐藏")
    component = fields.CharField(max_length=100, description="组件")
    keepalive = fields.BooleanField(default=True, description="存活")
    redirect = fields.CharField(max_length=100, null=True, description="重定向")

    class Meta:
        table = "menu"
        unique_together = (("parent_id", "name"), )


class Dept(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, description="部门名称", db_index=True)
    desc = fields.CharField(max_length=500, null=True, description="备注")
    is_deleted = fields.BooleanField(default=False, description="软删除标记", db_index=True)
    order = fields.IntField(default=0, description="排序", db_index=True)
    parent_id = fields.IntField(default=0, max_length=10, description="父部门ID", db_index=True)

    class Meta:
        table = "dept"
        unique_together = (("parent_id", "name"), )


class DeptClosure(BaseModel, TimestampMixin):
    ancestor = fields.IntField(description="父代", db_index=True)
    descendant = fields.IntField(description="子代", db_index=True)
    level = fields.IntField(default=0, description="深度", db_index=True)


class AuditLog(BaseModel, TimestampMixin):
    user_id = fields.IntField(description="用户ID", db_index=True)
    username = fields.CharField(max_length=64, default="", description="用户名称", db_index=True)
    module = fields.CharField(max_length=64, default="", description="功能模块", db_index=True)
    summary = fields.CharField(max_length=128, default="", description="请求描述", db_index=True)
    method = fields.CharField(max_length=10, default="", description="请求方法", db_index=True)
    path = fields.CharField(max_length=255, default="", description="请求路径", db_index=True)
    status = fields.IntField(default=-1, description="状态码", db_index=True)
    response_time = fields.IntField(default=0, description="响应时间(单位ms)", db_index=True)
    request_args = fields.JSONField(null=True, description="请求参数")
    response_body = fields.JSONField(null=True, description="返回数据")
