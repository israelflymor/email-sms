from packages.config.settings import settings
def parse_admin_api_keys() -> dict[str, str]:
    pairs = [x.strip() for x in settings.admin_api_keys.split(",") if x.strip()]
    result = {}
    for pair in pairs:
        if ":" not in pair:
            continue
        key, role = pair.split(":", 1)
        result[key.strip()] = role.strip()
    return result
def get_role_for_api_key(api_key: str) -> str | None:
    return parse_admin_api_keys().get(api_key)
