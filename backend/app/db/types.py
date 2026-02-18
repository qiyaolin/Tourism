from sqlalchemy.types import UserDefinedType


class GeometryPoint(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw: object) -> str:
        return "GEOMETRY(Point,4326)"
