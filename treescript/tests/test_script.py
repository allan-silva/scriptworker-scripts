import json
import mock
import os
import pytest

from scriptworker_client.exceptions import TaskError
from unittest.mock import MagicMock

import treescript.script as script


# helper constants, fixtures, functions {{{1
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
EXAMPLE_CONFIG = os.path.join(BASE_DIR, "config_example.json")


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


def read_file(path):
    with open(path, "r") as fh:
        return fh.read()


def get_conf_file(tmpdir, **kwargs):
    conf = json.loads(read_file(EXAMPLE_CONFIG))
    conf.update(kwargs)
    conf["work_dir"] = os.path.join(tmpdir, "work")
    conf["artifact_dir"] = os.path.join(tmpdir, "artifact")
    path = os.path.join(tmpdir, "new_config.json")
    with open(path, "w") as fh:
        json.dump(conf, fh)
    return path


async def die_async(*args, **kwargs):
    raise TaskError("Expected exception.")


# async_main {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "robustcheckout_works,raises,actions",
    (
        (False, TaskError, ["some_action"]),
        (True, None, ["some_action"]),
        (True, None, None),
    ),
)
async def test_async_main(tmpdir, mocker, robustcheckout_works, raises, actions):
    async def fake_validate_robustcheckout(_):
        return robustcheckout_works

    def action_fun(*args, **kwargs):
        return actions

    mocker.patch.object(script, "task_action_types", new=action_fun)
    mocker.patch.object(
        script, "validate_robustcheckout_works", new=fake_validate_robustcheckout
    )
    mocker.patch.object(script, "log_mercurial_version", new=noop_async)
    mocker.patch.object(script, "checkout_repo", new=noop_async)
    mocker.patch.object(script, "do_actions", new=noop_async)
    config = mock.MagicMock()
    task = mock.MagicMock()
    if raises:
        with pytest.raises(raises):
            await script.async_main(config, task)
    else:
        await script.async_main(config, task)


# get_default_config {{{1
def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c["work_dir"] == os.path.join(parent_dir, "work_dir")


# do_actions {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "push_scope,dry_run,push_expect_called",
    (
        (["push"], True, False),
        (["push"], False, True),
        ([], False, False),
        ([], True, False),
    ),
)
async def test_do_actions(mocker, push_scope, dry_run, push_expect_called):
    actions = ["tagging", "version_bump", "l10n_bump"]
    actions += push_scope
    called_tag = [False]
    called_bump = [False]
    called_l10n = [False]
    called_push = [False]

    async def mocked_tag(*args, **kwargs):
        called_tag[0] = True
        return True

    async def mocked_bump(*args, **kwargs):
        called_bump[0] = True
        return True

    async def mocked_l10n(*args, **kwargs):
        called_l10n[0] = True
        return True

    async def mocked_push(*args, **kwargs):
        called_push[0] = True
        return True

    mocker.patch.object(script, "checkout_repo", new=noop_async)
    mocker.patch.object(script, "strip_outgoing", new=noop_async)
    mocker.patch.object(script, "do_tagging", new=mocked_tag)
    mocker.patch.object(script, "bump_version", new=mocked_bump)
    mocker.patch.object(script, "l10n_bump", new=mocked_l10n)
    mocker.patch.object(script, "push", new=mocked_push)
    mocker.patch.object(script, "log_outgoing", new=noop_async)
    mocker.patch.object(script, "is_dry_run", return_value=dry_run)
    await script.do_actions({}, {}, actions, "/some/folder/here")
    assert called_tag[0]
    assert called_bump[0]
    assert called_l10n[0]
    assert called_push[0] is push_expect_called


@pytest.mark.asyncio
async def test_do_actions_no_changes(mocker):
    actions = ["push"]
    called_tag = [False]
    called_bump = [False]
    called_l10n = [False]
    called_push = [False]

    async def mocked_tag(*args, **kwargs):
        called_tag[0] = True
        return True

    async def mocked_bump(*args, **kwargs):
        called_bump[0] = True
        return True

    async def mocked_l10n(*args, **kwargs):
        called_l10n[0] = True
        return True

    async def mocked_push(*args, **kwargs):
        called_push[0] = True
        return True

    mocker.patch.object(script, "checkout_repo", new=noop_async)
    mocker.patch.object(script, "strip_outgoing", new=noop_async)
    mocker.patch.object(script, "do_tagging", new=mocked_tag)
    mocker.patch.object(script, "bump_version", new=mocked_bump)
    mocker.patch.object(script, "l10n_bump", new=mocked_l10n)
    mocker.patch.object(script, "push", new=mocked_push)
    mocker.patch.object(script, "log_outgoing", new=noop_async)
    mocker.patch.object(script, "is_dry_run", return_value=False)
    await script.do_actions({}, {}, actions, "/some/folder/here")
    assert not called_tag[0]
    assert not called_bump[0]
    assert not called_l10n[0]
    assert not called_push[0]


@pytest.mark.asyncio
async def test_do_actions_unknown(mocker):
    actions = ["unknown"]
    called_tag = [False]
    called_bump = [False]

    async def mocked_tag(*args, **kwargs):
        called_tag[0] = True

    async def mocked_bump(*args, **kwargs):
        called_bump[0] = True

    mocker.patch.object(script, "checkout_repo", new=noop_async)
    mocker.patch.object(script, "do_tagging", new=mocked_tag)
    mocker.patch.object(script, "bump_version", new=mocked_bump)
    mocker.patch.object(script, "log_outgoing", new=noop_async)
    with pytest.raises(NotImplementedError):
        await script.do_actions({}, {}, actions, "/some/folder/here")
    assert called_tag[0] is False
    assert called_bump[0] is False


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(script, "sync_main", sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(
        script.async_main, default_config=script.get_default_config()
    )
