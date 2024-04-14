# import json
import time
from datetime import datetime

import requests
from atlassian.bitbucket.cloud.common.builds import Build
from atlassian.bitbucket.cloud.repositories import Repository

# from cumulusci.core.dependencies.dependencies import parse_dependencies
# from cumulusci.core.dependencies.resolvers import get_static_dependencies
from cumulusci.core.exceptions import BitbucketException, TaskOptionsError
from cumulusci.core.bitbucket import get_commit
from cumulusci.tasks.bitbucket.base import BaseBitbucketTask
from cumulusci.oauth.salesforce import SANDBOX_LOGIN_URL


class CreateRelease(BaseBitbucketTask):

    task_options = {
        "version": {
            "description": "The managed package version number.  Ex: 1.2",
            "required": True,
        },
        "version_id": {
            "description": "The SubscriberPackageVersionId (04t) associated with this release.",
            "required": False,
        },
        "message": {
            "description": "The message to attach to the created git tag"
        },
        "release_content": {
            "description": "The content to include as the release body."
        },
        "dependencies": {
            "description": "List of dependencies to record in the tag message."
        },
        "commit": {
            "description": (
                "Override the commit used to create the release. "
                "Defaults to the current local HEAD commit"
            )
        },
        "resolution_strategy": {
            "description": "The name of a sequence of resolution_strategy (from project__dependency_resolutions) to apply to dynamic dependencies. Defaults to 'production'."
        },
        "package_type": {
            "description": "The package type of the project (either 1GP or 2GP)",
            "required": True,
        },
        "tag_prefix": {
            "description": "The prefix to use for the release tag created in github.",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.commit = self.options.get("commit", self.project_config.repo_commit)
        if not self.commit:
            message = "Could not detect the current commit from the local repo"
            self.logger.error(message)
            raise BitbucketException(message)
        if len(self.commit) != 40:
            raise TaskOptionsError("The commit option must be exactly 40 characters.")

    def _run_task(self):
        repo = self.get_repo()
        version = self.options["version"]
        tag_prefix = self.options.get("tag_prefix")
        tag_name = self.project_config.get_tag_for_version(tag_prefix, version)

        self._verify_release(repo, tag_name)
        self._verify_commit(repo)

        # Build tag message
        message = self.options.get("message", "Release of version {}".format(version))
        if self.options.get("version_id"):
            message += f"\n\nversion_id: {self.options['version_id']}"
        if self.options.get("package_type"):
            message += f"\n\npackage_type: {self.options['package_type']}"

        if self.options.get("dependencies") or self.project_config.project__dependencies:
            raise EnvironmentError("Dependencies are not supported in Bitbucket.")

        # dependencies = get_static_dependencies(
        #     self.project_config,
        #     dependencies=parse_dependencies(
        #         self.options.get("dependencies")
        #         or self.project_config.project__dependencies,
        #     ),
        #     resolution_strategy=self.options.get("resolution_strategy") or "production",
        # )
        # if dependencies:
        #     dependencies = [d.dict(exclude_none=True) for d in dependencies]
        #     message += "\n\ndependencies: {}".format(json.dumps(dependencies, indent=4))

        try:
            repo.tags.get(tag_name)
        except requests.exceptions.HTTPError as e:
            # Create the annotated tag
            if e.response.status_code == 404:
                data = {
                    "type": "tag",
                    "name": tag_name,
                    "target": {"hash": self.commit},
                    "message": message,
                }
                repo.tags.post(None, data)

                # Sleep for Github to catch up with the fact that the tag actually exists!
                time.sleep(3)

        prerelease = tag_name.startswith(self.project_config.project__git__prefix_beta)

        # TODO: Remove this github release stuff
        release_parameters = {
            "tag_name": tag_name,
            "name": version,
            "prerelease": prerelease,
        }
        if "release_content" in self.options:
            release_parameters["body"] = self.options["release_content"]
        url = f"{SANDBOX_LOGIN_URL}/packaging/installPackage.apexp?p0={self.options.get('version_id')}"
        release = repo.commits.get(self.commit).add_build(
            key="release",
            description=message,
            state=Build.STATE_SUCCESSFUL,
            url=url
        )
        self.logger.info(f"Created release {release.get('name')} at {release.get('links').get('self').get('href')}")

    def _verify_release(self, repo: Repository, tag_name: str) -> None:
        """Make sure release doesn't already exist"""
        try:
            tag = repo.tags.get(tag_name)
            commit = get_commit(repo, tag.get_data('target').get('hash'))
            release: Build = commit.get_build(key="release")
        except requests.exceptions.HTTPError:
            pass
        else:
            message = f"Release {tag_name} already exists at {tag.get_links('self')}"
            self.logger.error(message)
            raise BitbucketException(message)

    def _verify_commit(self, repo: Repository) -> None:
        """Verify that the commit exists on the remote."""
        get_commit(repo, self.commit)
