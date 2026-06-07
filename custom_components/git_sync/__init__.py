"""Git Sync — pull main from GitHub into /config on the HA host.

Exposes one service, ``git_sync.pull``, that fetches origin and
hard-resets /config to origin/main. The GitHub Actions deploy workflow
calls this service after each merge so new commits land on the HA host
without depending on the SSH addon's stdin support (removed for
core_ssh) or the git binary (no longer shipped in the HA Core
container image).

Implemented with dulwich (pure-Python git) so it has no system-binary
or addon dependency.
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "git_sync"
CONFIG_DIR = "/config"
REMOTE = "origin"
BRANCH = "main"

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the git_sync.pull service."""

    async def handle_pull(_: ServiceCall) -> None:
        await hass.async_add_executor_job(_fast_forward_to_origin_main)

    hass.services.async_register(DOMAIN, "pull", handle_pull)
    return True


def _fast_forward_to_origin_main() -> None:
    """Fetch origin and hard-reset /config to origin/main.

    Runs in the executor (dulwich is sync). Hard reset is intentional:
    deploy semantics treat main as source of truth, so any uncommitted
    edits on the HA host are discarded.
    """
    from dulwich import porcelain
    from dulwich.repo import Repo

    repo = Repo(CONFIG_DIR)
    porcelain.fetch(repo, REMOTE)

    remote_ref = f"refs/remotes/{REMOTE}/{BRANCH}".encode()
    local_ref = f"refs/heads/{BRANCH}".encode()
    target_sha = repo.refs[remote_ref]

    repo.refs[local_ref] = target_sha
    repo.refs.set_symbolic_ref(b"HEAD", local_ref)
    porcelain.reset(repo, "hard", target_sha)

    _LOGGER.info(
        "git_sync.pull synced /config to %s/%s @ %s",
        REMOTE,
        BRANCH,
        target_sha.decode()[:7],
    )
