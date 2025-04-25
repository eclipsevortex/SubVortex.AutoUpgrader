import subvortex.auto_upgrader.src.constants as sauc


def get_tag():
    if "alpha" == sauc.SV_PRERELEASE_TYPE:
        return "dev"

    if "rc" == sauc.SV_PRERELEASE_TYPE:
        return "stable"

    return "latest"
