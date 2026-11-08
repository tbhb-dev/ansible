# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

from ansible_collections.tbhb.dsm.plugins.modules import share_quota_info
from ansible_collections.tbhb.dsm.tests.unit.conftest import QUOTA_REPLY


def test_reads_user_quota(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Quota", "get", QUOTA_REPLY)
    rc, result = run_module(share_quota_info.main, {"name": "alice"})
    assert rc == 0
    assert result["changed"] is False
    assert result["quotas"] == [
        {"share": "archive", "volume": "/volume1", "quota": 0},
        {"share": "projects", "volume": "/volume1", "quota": 1024},
    ]
    (call,) = fake_dsm.calls_to("SYNO.Core.Quota", "get")
    assert call["name"] == "alice"
    assert call["subject_type"] == "user"


def test_reads_group_quota(fake_dsm, run_module):
    reply = {"success": True, "data": {"group_quota": QUOTA_REPLY["data"]["user_quota"]}}
    fake_dsm.reply("SYNO.Core.Quota", "get", reply)
    rc, result = run_module(share_quota_info.main, {"name": "users", "subject_type": "group"})
    assert rc == 0
    assert len(result["quotas"]) == 2
    assert fake_dsm.calls[0]["subject_type"] == "group"


def test_share_filter(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Quota", "get", QUOTA_REPLY)
    result = run_module(share_quota_info.main, {"name": "alice", "share": ["projects", "missing"]})[1]
    assert [q["share"] for q in result["quotas"]] == ["projects"]


def test_reply_without_the_expected_key_fails(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Quota", "get", {"success": True, "data": {"group_quota": []}})
    rc, result = run_module(share_quota_info.main, {"name": "alice"})
    assert rc == 1
    assert "user_quota" in result["msg"]


def test_works_in_check_mode(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Quota", "get", QUOTA_REPLY)
    rc = run_module(share_quota_info.main, {"name": "alice", "_ansible_check_mode": True})[0]
    assert rc == 0


def test_dsm_error_code_is_reported(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Quota", "get", {"success": False, "error": {"code": 3101}})
    rc, result = run_module(share_quota_info.main, {"name": "ghost"})
    assert rc == 1
    assert result["dsm_error_code"] == 3101


def test_malformed_json_fails(fake_dsm, run_module):
    fake_dsm.reply("SYNO.Core.Quota", "get", "")
    rc, result = run_module(share_quota_info.main, {"name": "alice"})
    assert rc == 1
    assert "not valid JSON" in result["msg"]
