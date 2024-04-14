from atlassian.bitbucket.cloud.repositories import Repository
from cumulusci.core.bitbucket import get_bitbucket_cloud_api
from cumulusci.core.tasks import BaseTask


class BaseBitbucketTask(BaseTask):
    def _init_task(self):
        super()._init_task()
        self.bitbucket_config = self.project_config.keychain.get_service("bitbucket")
        self.bitbucket = get_bitbucket_cloud_api(
            self.project_config.keychain
        )

    def get_repo(self) -> Repository:
        workspace = self.bitbucket.workspaces.get(
            self.project_config.repo_owner
        )
        return workspace.repositories.get(self.project_config.repo_name)
