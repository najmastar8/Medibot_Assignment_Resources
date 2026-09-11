ROLE_COLLECTIONS = {
    "doctor": ["general", "clinical", "nursing"],
    "nurse": ["general", "nursing"],
    "billing_executive": ["general", "billing"],
    "technician": ["general", "equipment"],
    "admin": ["general", "clinical", "nursing", "billing", "equipment"],
}

ALL_ROLES = list(ROLE_COLLECTIONS.keys())


def get_role_access(role: str) -> list[str]:
    return list(ROLE_COLLECTIONS.get(role, ["general"]))


def can_access_collection(role: str, collection: str) -> bool:
    if role == "admin":
        return True
    return collection in get_role_access(role)


def build_qdrant_filter(role: str) -> dict:
    allowed = get_role_access(role)
    return {
        "must": [
            {
                "key": "access_roles",
                "match": {"any": [role, "admin"]},
            },
            {"key": "collection", "match": {"any": allowed}},
        ]
    }


def get_rbac_refusal(role: str) -> str:
    allowed = ", ".join(get_role_access(role))
    return (
        f"As a {role}, you don't have access to billing or equipment documents. "
        f"I can only answer questions from the {allowed} collections."
    )
