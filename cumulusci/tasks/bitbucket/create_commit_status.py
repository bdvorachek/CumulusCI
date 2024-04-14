from atlassian.bitbucket.cloud.common.builds import Build

from cumulusci.tasks.bitbucket.base import BaseBitbucketTask


def _is_valid_status(status):
    return status in [Build.STATE_FAILED, Build.STATE_INPROGRESS, Build.STATE_STOPPED, Build.STATE_SUCCESSFUL]


class CreatePackageDataCommitStatus(BaseBitbucketTask):
    task_options = {
        "context": {
            "description": "Name of the commit status context",
            "required": True,
        },
        "version_id": {
            "description": "Package version id",
            "required": False
        },
        "package_type": {
            "description": "Type of package (1GP or 2GP)",
            "required": False,
            "default": "2GP",
        },
        "status": {
            "description": "The status of the commit",
            "required": False,
            "default": "SUCCESSFUL",
        },
    }

    def _run_task(self):
        context = self.options["context"]
        status = (self.options.get("status") or self.task_options["status"]["default"]).upper()
        if not _is_valid_status(status):
            raise ValueError(f"Invalid status: {status}")

        self.api_version = self.project_config.project__api_version
        repo = self.get_repo()

        commit_sha = self.project_config.repo_commit
        dependencies = []
        version_id = self.options.get("version_id")
        package_type = self.options.get("package_type") or self.task_options["package_type"]["default"]
        try:
            commit = repo.commits.get(commit_sha)
            self.logger.debug(f"Setting commit status for commit {commit_sha} to {status} with url {self.project_config.repo_url}")
            commit.add_build(key=context,
                             state=status,
                             url=f'https://test.salesforce.com/packaging/installPackage.apexp?p0={version_id}',
                             description=f"""version_id: {version_id}
package_type: {package_type}""")
        except Exception as e:
            self.logger.error(e)
            self.logger.error(
                "Something went wrong when setting the commit status. "
            )

        self.return_values = {"dependencies": dependencies, "version_id": version_id, "package_type": package_type}
        return ''

