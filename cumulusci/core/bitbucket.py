import io
import re
from atlassian.bitbucket import Cloud
from atlassian.bitbucket.cloud.common.builds import Build
from atlassian.bitbucket.cloud.repositories import Repository
from atlassian.bitbucket.cloud.repositories.commits import Commit
from atlassian.bitbucket.cloud.repositories.refs import Tag

from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load
import pdb

VERSION_ID_RE = re.compile(r"version_id: (\S+)")
PACKAGE_TYPE_RE = re.compile(r"^package_type: (.*)$", re.MULTILINE)

def get_commit(repo: Repository, commit_sha: str) -> Commit:
    return repo.commits.get(commit_sha)


def get_version_id_from_commit(repo: Repository, commit_sha: str, context: str) -> Build:
    commit = get_commit(repo, commit_sha)
    build: Build = commit.get_build(key=context)
    if build is None:
        raise Exception(f"Could not find build for {context} in commit {commit_sha}")
    if build.successful:
        match = VERSION_ID_RE.search(build.description)
        if match:
            return match.group(1)
        else:
            raise Exception(f"Could not find version_id in build description for {context} in commit {commit_sha}")


def get_version_id_from_tag(repo: Repository, tag_name: str) -> str:
    tag = get_tag_by_name(repo, tag_name)
    for line in tag.get("message").split("\n"):
        if line.startswith("version_id:"):
            return line.split(":")[1].strip()


def get_tag_by_name(repo: Repository, tag_name: str) -> Tag:
    return repo.tags.get(tag_name)


def validate_service(options: dict, keychain) -> dict:
    username = options["username"]
    app_password = options["app_password"]

    try:
        authed_user = Cloud(username=username, password=app_password, cloud=True)
        authed_user.get('user')
    except Exception as e:
        raise Exception(f"Failed to authenticate to Bitbucket: {e}")

    return options


def get_bitbucket_cloud_api_for_repo(keychain, owner, name, session=None) -> Repository:
    cloud = get_bitbucket_cloud_api(keychain)
    return cloud.workspaces.get(owner).repositories.get(name)


def get_bitbucket_cloud_api(keychain) -> Cloud:
    service_config = keychain.get_service("bitbucket")
    return Cloud(username=service_config.username, password=service_config.app_password, cloud=True)


def find_repo_feature_prefix(repo: Repository) -> str:
    main_branch = repo.get_data("mainbranch").get("name")
    ref = repo.branches.get(main_branch).get_data("target").get("hash")
    contents = repo.get(f"/src/{ref}/cumulusci.yml")
    head_cumulusci_yml = cci_safe_load(io.StringIO(contents))
    return (
        head_cumulusci_yml.get("project", {})
        .get("git", {})
        .get("prefix_feature", "feature/")
    )

