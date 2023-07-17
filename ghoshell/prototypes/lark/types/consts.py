class UserIdType:
    # 标识一个用户在某个应用中的身份。同一个用户在不同应用中的 Open ID 不同。
    OPEN_ID = "open_id"
    # 标识一个用户在某个应用开发商下的身份。同一用户在同一开发商下的应用中的 Union ID 是相同的，在不同开发商下的应用中的 Union ID 是不同的。
    # 通过 Union ID，应用开发商可以把同个用户在多个应用中的身份关联起来。
    UNION_ID = "union_id"

    # 标识一个用户在某个租户内的身份。同一个用户在租户 A 和租户 B 内的 User ID 是不同的。
    # 在同一个租户内，一个用户的 User ID 在所有应用（包括商店应用）中都保持一致。User ID 主要用于在不同的应用间打通用户数据。
    USER_ID = "user_id"


class DepartmentIdType:
    # 以自定义department_id来标识部门
    DEPARTMENT_ID = "department_id"

    # 以open_department_id来标识部门
    OPEN_DEPARTMENT_ID = "open_department_id"
