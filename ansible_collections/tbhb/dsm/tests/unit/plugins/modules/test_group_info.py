# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

from ansible_collections.tbhb.dsm.plugins.modules import group_info


def test_lists_groups_with_members(standard_accounts, run_module):
    rc, result = run_module(group_info.main)
    assert rc == 0
    assert result["changed"] is False
    assert result["groups"] == [
        {"name": "administrators", "gid": 101, "description": "System default admin group", "members": ["alice"]},
        {"name": "users", "gid": 100, "description": "System default group", "members": ["alice", "bob"]},
    ]


def test_name_filter_skips_other_member_calls(standard_accounts, run_module):
    rc, result = run_module(group_info.main, {"name": ["users", "missing"]})
    assert rc == 0
    assert [g["name"] for g in result["groups"]] == ["users"]
    assert [c["group"] for c in standard_accounts.calls_to("SYNO.Core.Group.Member")] == ["users"]


def test_works_in_check_mode(standard_accounts, run_module):
    rc, result = run_module(group_info.main, {"_ansible_check_mode": True})
    assert rc == 0
    assert len(result["groups"]) == 2


def test_dsm_error_code_is_reported(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Group", "list", {"success": False, "error": {"code": 119}})
    rc, result = run_module(group_info.main)
    assert rc == 1
    assert result["failed"] is True
    assert result["dsm_error_code"] == 119


def test_dsm_error_on_member_call(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Group", "list", {"success": True, "data": {"groups": [{"name": "users", "gid": 100}]}})
    fake_dsm.reply("SYNO.Core.Group.Member", "list", {"success": False, "error": {"code": 3301}})
    rc, result = run_module(group_info.main)
    assert rc == 1
    assert result["dsm_error_code"] == 3301


def test_malformed_json_fails_with_the_output(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Group", "list", "<html>not json")
    rc, result = run_module(group_info.main)
    assert rc == 1
    assert "not valid JSON" in result["msg"]
    assert result["output"] == "<html>not json"


def test_nonzero_exit_fails(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Group", "list", "", rc=1, stderr="permission denied")
    rc, result = run_module(group_info.main)
    assert rc == 1
    assert result["rc"] == 1
    assert result["stderr"] == "permission denied"
