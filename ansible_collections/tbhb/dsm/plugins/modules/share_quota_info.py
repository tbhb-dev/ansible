#!/usr/bin/python
# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

DOCUMENTATION = r"""
module: share_quota_info
short_description: Read the share quotas of a user or group on a Synology DSM NAS
version_added: "0.1.0"
description:
  - Reads the quota that DSM holds for one local user or group, per volume and per share, by running C(synowebapi --exec) on the managed node.
  - Read-only. It changes nothing on the NAS.
  - Needs a user that may run C(synowebapi), which on DSM is root. Use C(become).
  - Synology publishes no guide for this API. Only the group form of the call appears in the community wrapper this module is modelled on.
  - So the user form is unverified. See the module source.
options:
  name:
    description: The local user or group to read the quota of.
    type: str
    required: true
  subject_type:
    description:
      - Whether O(name) is a user or a group.
      - V(group) is the form shown in the community wrapper. V(user) is unverified against a real reply.
    type: str
    choices: [user, group]
    default: user
  share:
    description:
      - Return only the quota rows for these shares.
      - A share that has no quota row is left out of the result and is not an error.
    type: list
    elements: str
    required: false
attributes:
  check_mode:
    support: full
    description: The module only reads, so it runs the same way in check mode.
  diff_mode:
    support: none
    description: The module changes nothing, so there is no diff.
author:
  - Tony Burns (@tbhb)
"""

EXAMPLES = r"""
- name: Read alice's quota on every share
  tbhb.dsm.share_quota_info:
    name: alice
  become: true
  register: quota

- name: Read the users group's quota on one share
  tbhb.dsm.share_quota_info:
    name: users
    subject_type: group
    share:
      - projects
  become: true
"""

RETURN = r"""
quotas:
  description: One row per share that DSM reports a quota for, sorted by volume then share.
  returned: success
  type: list
  elements: dict
  contains:
    share:
      description: The share name.
      type: str
      sample: projects
    volume:
      description: The volume the quota applies on.
      type: str
      sample: /volume1
    quota:
      description:
        - The quota as DSM reports it. The unit is unverified; the community wrapper does not state it.
        - V(0) is expected to mean no limit, which is also unverified.
      type: int
      sample: 1024
"""

# API reference. Synology publishes no guide for SYNO.Core.Quota. It is cited
# to the community wrapper N4S4/synology-api, synology_api/core_group.py,
# get_quota:
#   SYNO.Core.Quota  version=1  method=get  name=<group>  subject_type=group
#       support_share_quota=true
#   The reply carries data.group_quota, a list of {volume, quota_status,
#   deduped, support_share_quota, shares: [{name, description, quota}]}.
# Unverified, because the wrapper shows only the group form:
#   - subject_type=user and the reply key data.user_quota. The module reads
#     user_quota for a user and group_quota for a group, and fails if the key is
#     missing rather than guess.
#   - the unit of "quota", and that 0 means unlimited.

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.tbhb.dsm.plugins.module_utils.synowebapi import (
    SynoWebApi,
    SynoWebApiError,
    SynoWebApiResponseError,
    fail_json_from_error,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "name": {"type": "str", "required": True},
            "subject_type": {"type": "str", "choices": ["user", "group"], "default": "user"},
            "share": {"type": "list", "elements": "str"},
        },
        supports_check_mode=True,
    )
    subject_type = module.params["subject_type"]
    wanted = module.params["share"]
    key = "%s_quota" % subject_type
    client = SynoWebApi(module)

    try:
        data = client.call(
            "SYNO.Core.Quota",
            "get",
            version=1,
            params={"name": module.params["name"], "subject_type": subject_type, "support_share_quota": True},
        )
        if not isinstance(data.get(key), list):
            raise SynoWebApiResponseError("reply from SYNO.Core.Quota get has no %r list" % key)
    except SynoWebApiError as exc:
        fail_json_from_error(module, exc)

    quotas = []
    for volume in data[key]:
        for share in volume.get("shares", []):
            if wanted is not None and share.get("name") not in wanted:
                continue
            quotas.append({"share": share.get("name"), "volume": volume.get("volume"), "quota": share.get("quota")})
    module.exit_json(changed=False, quotas=sorted(quotas, key=lambda q: (q["volume"] or "", q["share"] or "")))


if __name__ == "__main__":
    main()
