# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

from ansible_collections.tbhb.dsm.plugins.modules import user_info


def test_lists_users_with_groups(standard_accounts, run_module):
    rc, result = run_module(user_info.main)
    assert rc == 0
    assert result["changed"] is False
    assert [u["name"] for u in result["users"]] == ["alice", "bob"]
    alice, bob = result["users"]
    assert alice["groups"] == ["administrators", "users"]
    assert alice["uid"] == 1026
    assert alice["email"] == "alice@example.com"
    assert bob["groups"] == ["users"]


def test_shell_is_null_when_dsm_gives_none(standard_accounts, run_module):
    result = run_module(user_info.main)[1]
    assert all(u["shell"] is None for u in result["users"])


def test_shell_is_passed_through_when_dsm_gives_one(fake_dsm, run_module):
    fake_dsm.reply(
        "SYNO.Core.User", "list", {"success": True, "data": {"users": [{"name": "alice", "shell": "/bin/sh"}]}}
    )
    fake_dsm.reply("SYNO.Core.Group", "list", {"success": True, "data": {"groups": []}})
    result = run_module(user_info.main)[1]
    assert result["users"][0]["shell"] == "/bin/sh"
    assert result["users"][0]["groups"] == []


def test_name_filter(standard_accounts, run_module):
    rc, result = run_module(user_info.main, {"name": ["bob", "missing"]})
    assert rc == 0
    assert [u["name"] for u in result["users"]] == ["bob"]


def test_requests_local_users_only(standard_accounts, run_module):
    run_module(user_info.main)
    (call,) = standard_accounts.calls_to("SYNO.Core.User", "list")
    assert call["type"] == "local"


def test_works_in_check_mode(standard_accounts, run_module):
    rc, result = run_module(user_info.main, {"_ansible_check_mode": True})
    assert rc == 0
    assert len(result["users"]) == 2


def test_dsm_error_code_is_reported(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.User", "list", {"success": False, "error": {"code": 105}})
    rc, result = run_module(user_info.main)
    assert rc == 1
    assert result["dsm_error_code"] == 105


def test_malformed_json_fails(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.User", "list", '{"success": true, "data": ')
    rc, result = run_module(user_info.main)
    assert rc == 1
    assert "not valid JSON" in result["msg"]
