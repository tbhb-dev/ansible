# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

from ansible_collections.tbhb.dsm.plugins.modules import share_info
from ansible_collections.tbhb.dsm.tests.unit.conftest import SHARES_REPLY, permission_reply

USER_ITEMS = [
    {"name": "alice", "is_writable": True, "is_readonly": False, "is_deny": False, "is_admin": False},
    {"name": "bob", "is_writable": False, "is_readonly": True, "is_deny": False, "is_admin": False},
    {"name": "carol", "is_writable": False, "is_readonly": False, "is_deny": True, "is_admin": False},
    {"name": "dave", "is_writable": False, "is_readonly": False, "is_deny": False, "is_admin": False},
]
GROUP_ITEMS = [{"name": "users", "is_writable": False, "is_readonly": True, "is_deny": False}]


def test_lists_shares_without_permission_calls(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Share", "list", SHARES_REPLY)
    rc, result = run_module(share_info.main)
    assert rc == 0
    assert result["changed"] is False
    assert result["shares"] == [
        {"name": "archive", "description": "", "volume_path": "/volume2", "uuid": "uuid-2", "permissions": {}},
        {"name": "projects", "description": "Project files", "volume_path": "/volume1", "uuid": "uuid-1", "permissions": {}},
    ]
    assert fake_dsm.calls_to("SYNO.Core.Share.Permission") == []


def test_permissions_for_named_users_and_groups(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Share", "list", SHARES_REPLY)
    fake_dsm.reply("SYNO.Core.Share.Permission", "list", permission_reply(USER_ITEMS), user_group_type="local_user")
    fake_dsm.reply("SYNO.Core.Share.Permission", "list", permission_reply(GROUP_ITEMS), user_group_type="local_group")
    rc, result = run_module(
        share_info.main,
        {"name": ["projects"], "users": ["alice", "bob", "carol", "dave", "nobody"], "groups": ["users"]},
    )
    assert rc == 0
    (share,) = result["shares"]
    assert share["permissions"] == {
        "users": {"alice": "read_write", "bob": "read_only", "carol": "deny", "dave": "none"},
        "groups": {"users": "read_only"},
    }
    assert {c["name"] for c in fake_dsm.calls_to("SYNO.Core.Share.Permission")} == {"projects"}


def test_permission_paging(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Share", "list", {"success": True, "data": {"shares": [{"name": "projects"}]}})
    fake_dsm.reply(
        "SYNO.Core.Share.Permission", "list", permission_reply(USER_ITEMS[:2], total=3), offset="0"
    )
    fake_dsm.reply(
        "SYNO.Core.Share.Permission", "list", permission_reply([USER_ITEMS[2]], total=3), offset="2"
    )
    result = run_module(share_info.main, {"users": ["alice", "carol"]})[1]
    assert result["shares"][0]["permissions"]["users"] == {"alice": "read_write", "carol": "deny"}
    assert [c["offset"] for c in fake_dsm.calls_to("SYNO.Core.Share.Permission")] == ["0", "2"]


def test_endless_paging_is_cut_off(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Share", "list", {"success": True, "data": {"shares": [{"name": "projects"}]}})
    fake_dsm.reply("SYNO.Core.Share.Permission", "list", permission_reply(USER_ITEMS[:1], total=10**9))
    rc, result = run_module(share_info.main, {"users": ["alice"]})
    assert rc == 1
    assert "did not end" in result["msg"]


def test_works_in_check_mode(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Share", "list", SHARES_REPLY)
    rc, result = run_module(share_info.main, {"_ansible_check_mode": True})
    assert rc == 0
    assert len(result["shares"]) == 2


def test_dsm_error_code_is_reported(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Share", "list", {"success": False, "error": {"code": 402}})
    rc, result = run_module(share_info.main)
    assert rc == 1
    assert result["dsm_error_code"] == 402


def test_dsm_error_on_permission_call(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Share", "list", SHARES_REPLY)
    fake_dsm.reply("SYNO.Core.Share.Permission", "list", {"success": False, "error": {"code": 3300}})
    rc, result = run_module(share_info.main, {"users": ["alice"]})
    assert rc == 1
    assert result["dsm_error_code"] == 3300


def test_malformed_json_fails(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Share", "list", "[]")
    rc, result = run_module(share_info.main)
    assert rc == 1
    assert "no boolean 'success'" in result["msg"]
