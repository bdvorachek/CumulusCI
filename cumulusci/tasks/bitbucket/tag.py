from datetime import datetime

from atlassian.bitbucket.cloud.repositories.refs import Tag

from cumulusci.core.bitbucket import get_tag_by_name
from cumulusci.tasks.bitbucket.base import BaseBitbucketTask


class CloneTag(BaseBitbucketTask):
    task_options = {  # TODO: should use `class Options instead`
        "src_tag": {
            "description": "The source tag to clone.  Ex: beta/1.0-Beta_2",
            "required": True,
        },
        "tag": {
            "description": "The new tag to create by cloning the src tag.  Ex: release/1.0",
            "required": True,
        },
    }

    def _run_task(self):
        src_tag_name = self.options["src_tag"]
        repo = self.get_repo()
        src_tag = get_tag_by_name(repo, src_tag_name)

        tag: Tag = repo.tags.create(
            self.options["tag"],
            message=f"Cloned from {src_tag_name}",
            sha=src_tag.sha,
            obj_type="commit",
            tagger={
                "name": self.bitbucket_config.username,
                "email": self.bitbucket_config.email,
                "date": f"{datetime.utcnow().isoformat()}Z",
            },
        )
        self.logger.info(f"Tag {self.options['tag']} created by cloning {src_tag_name}")

        return tag
