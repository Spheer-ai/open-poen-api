resource User {
    permissions = ["create", "read", "edit", "delete"];
    roles = ["super_user", "user_owner", "user"];

    "create" if "super_user";
    "delete" if "super_user";
    "edit" if "user_owner";
    "read" if "user";

    "user" if "super_user";
    "user_owner" if "super_user";
    "user" if "user_owner";
}

actor User {
}

has_role(user: User, name: String, _resource: Resource) if
    user.role = name;

allow(actor, action, resource) if
    has_permission(actor, action, resource);
