# import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.controllers.user import user_controller
from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth
# from app.log.log import logger
from app.models.admin import Api, Menu, Role, User
from app.schemas.base import Fail, Success
from app.schemas.login import *
from app.schemas.users import UpdatePassword
from app.settings import settings
from app.utils.jwt_utils import create_access_token
from app.utils.password import get_password_hash, verify_password

router = APIRouter()


@router.post("/access_token", summary="获取token")
async def login_access_token(credentials: CredentialsSchema):
    user: User = await user_controller.authenticate(credentials)
    await user_controller.update_last_login(user.id)
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + access_token_expires

    data = JWTOut(
        access_token=create_access_token(
            data=JWTPayload(
                user_id=user.id,
                username=user.username,
                is_superuser=user.is_superuser,
                exp=expire,
            )
        ),
        username=user.username,
    )
    return Success(data=data.model_dump())


@router.get("/userinfo", summary="查看用户信息", dependencies=[DependAuth])
async def get_userinfo():
    user_id = CTX_USER_ID.get()
    user_obj = await user_controller.get(id=user_id)
    data = await user_obj.to_dict(exclude_fields=["password"])
    data["avatar"] = "https://avatars.githubusercontent.com/u/54677442?v=4"
    return Success(data=data)


@router.get("/usermenu", summary="查看用户菜单", dependencies=[DependAuth])
async def get_user_menu():
    user_id = CTX_USER_ID.get()
    user_obj = await User.filter(id=user_id).first()
    
    menus: list[Menu] = []
    if user_obj.is_superuser:
        menus = await Menu.all()
    else:
        role_objs: list[Role] = await user_obj.roles
        for role_obj in role_objs:
            menu = await role_obj.menus
            menus.extend(menu)
        menus = list(set(menus))
        
    # 收集所有需要显示的父菜单ID（包括子菜单对应的父菜单）
    parent_menu_ids = set()
    for menu in menus:
        if menu.parent_id == 0:
            # 直接拥有权限的父菜单
            parent_menu_ids.add(menu.id)
        else:
            # 子菜单：需要显示其父菜单
            parent_menu_ids.add(menu.parent_id)

    # 获取所有需要显示的父菜单对象
    parent_menus: list[Menu] = await Menu.filter(id__in=list(parent_menu_ids), parent_id=0)
    
    res = []
    for parent_menu in parent_menus:
        parent_menu_dict = await parent_menu.to_dict()
        parent_menu_dict["children"] = []
        # 强制显示父菜单，即使只有一个子菜单
        parent_menu_dict["alwaysShow"] = True
        
        for menu in menus:
            if menu.parent_id == parent_menu.id:
                parent_menu_dict["children"].append(await menu.to_dict())
        
        # 只有当父菜单有可见的子菜单时才添加到结果中
        # 或者它是顶级菜单，并且不仅是个容器 (Component不是Layout)
        if parent_menu_dict["children"] or (
            parent_menu.id in [m.id for m in menus if m.parent_id == 0] 
            and parent_menu.component != "Layout"
        ):
            res.append(parent_menu_dict)
            
    return Success(data=res)


@router.get("/userapi", summary="查看用户API", dependencies=[DependAuth])
async def get_user_api():
    user_id = CTX_USER_ID.get()
    user_obj = await User.filter(id=user_id).first()
    if user_obj.is_superuser:
        api_objs: list[Api] = await Api.all()
        apis = [api.method.lower() + api.path for api in api_objs]
        return Success(data=apis)
    role_objs: list[Role] = await user_obj.roles
    apis = []
    for role_obj in role_objs:
        api_objs: list[Api] = await role_obj.apis
        apis.extend([api.method.lower() + api.path for api in api_objs])
    apis = list(set(apis))
    return Success(data=apis)


@router.post("/update_password", summary="修改密码", dependencies=[DependAuth])
async def update_user_password(req_in: UpdatePassword):
    user_id = CTX_USER_ID.get()
    user = await user_controller.get(user_id)
    verified = verify_password(req_in.old_password, user.password)
    if not verified:
        return Fail(msg="旧密码验证错误！")
    user.password = get_password_hash(req_in.new_password)
    await user.save()
    return Success(msg="修改成功")
