from app.models.enums import EnumBase, MethodType


class SampleEnum(EnumBase):
    A = "a"
    B = "b"
    C = "c"


def test_enum_get_member_values():
    values = SampleEnum.get_member_values()
    assert values == ["a", "b", "c"]


def test_method_type_values():
    assert MethodType.GET == "GET"
    assert MethodType.POST == "POST"
    assert MethodType.PUT == "PUT"
    assert MethodType.DELETE == "DELETE"
    assert MethodType.PATCH == "PATCH"
