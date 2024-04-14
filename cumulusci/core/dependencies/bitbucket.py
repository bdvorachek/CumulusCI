import functools
import io
import re
from typing import Optional, Tuple

from github3.exceptions import NotFoundError
from atlassian.bitbucket.cloud.repositories import Repository
from atlassian.bitbucket.cloud.repositories.refs import Tag

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.versions import PackageType
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

PACKAGE_TYPE_RE = re.compile(r"^package_type: (.*)$", re.MULTILINE)
VERSION_ID_RE = re.compile(r"^version_id: (04t[a-zA-Z0-9]{12,15})$", re.MULTILINE)


def get_repo(bitbucket: str, context: BaseProjectConfig) -> Repository:
    try:
        repo = context.get_repo_from_url(bitbucket)
    except NotFoundError:
        repo = None

    if repo is None:
        raise DependencyResolutionError(
            f"We are unable to find the repository at {bitbucket}. Please make sure the URL is correct, that your GitHub user has read access to the repository, and that your GitHub personal access token includes the “repo” scope."
        )
    return repo


@functools.lru_cache(50)
def get_remote_project_config(repo: Repository, ref: str) -> BaseProjectConfig:
    contents = repo.get(f"/src/{ref}/cumulusci.yml")
    contents_io = io.StringIO(contents)
    contents_io.url = f"cumulusci.yml from {repo.get_data('full_name')}"  # for logging
    return BaseProjectConfig(None, cci_safe_load(contents_io))


def get_package_data(config: BaseProjectConfig):
    namespace = config.project__package__namespace
    package_name = (
        config.project__package__name_managed
        or config.project__package__name
        or "Package"
    )

    return package_name, namespace


def get_package_details_from_tag(
    tag: Tag,
) -> Tuple[Optional[str], Optional[PackageType]]:
    message = tag.get_data('message')
    version_id = VERSION_ID_RE.search(message)
    if version_id:
        version_id = version_id.group(1)
    package_type = PACKAGE_TYPE_RE.search(message)
    if package_type:
        package_type = PackageType(package_type.group(1))

    return version_id, package_type
