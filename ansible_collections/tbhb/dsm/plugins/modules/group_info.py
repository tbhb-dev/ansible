#!/usr/bin/python
# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

DOCUMENTATION = r"""
module: group_info
short_description: Read the local groups of a Synology DSM NAS
version_added: "0.1.0"
description:
  - Lists the local groups on a DSM NAS and the users in each, by running C(synowebapi --exec) on the managed node.
  - Read-only. It changes nothing on the NAS.
  - Needs a user that may run C(synowebapi), which on DSM is root. Use C(become).
  - Synology publishes no guide for these APIs. See the module source for the references and for what is unverified.
options:
  name:
    description:
      - Return only the groups with these names.
      - A name that matches no group is left out of the result and is not an error.
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
- name: Read every local group
  tbhb.dsm.group_info:
  become: true
  register: groups

- name: Read two groups
  tbhb.dsm.group_info:
    name:
      - administrators
      - users
  become: true
"""

RETURN = r"""
groups:
  description: The local groups, sorted by name.
  returned: success
  type: list
  elements: dict
  contains:
    name:
      description: The group name.
      type: str
      sample: users
    gid:
      description: The numeric group ID.
      type: int
      sample: 100
    description:
      description: The group description.
      type: str
      sample: System default group
    members:
      description: The names of the users in the group, sorted.
      type: list
      elements: str
      sample: ["alice", "bob"]
"""

# API references. Synology publishes no guide for SYNO.Core.*. Both are cited to
# the community wrapper N4S4/synology-api, synology_api/core_group.py:
#   SYNO.Core.Group         method=list  (get_groups)   cited; version unverified
#   SYNO.Core.Group.Member  method=list  (get_users)    cited; version unverified

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.tbhb.dsm.plugins.module_utils.accounts import list_group_members, list_groups
from ansible_collections.tbhb.dsm.plugins.module_utils.synowebapi import (
    SynoWebApi,
    SynoWebApiError,
    fail_json_from_error,
)


def main():
    module = AnsibleModule(
        argument_spec={"name": {"type": "list", "elements": "str"}},
        supports_check_mode=True,
    )
    wanted = module.params["name"]
    client = SynoWebApi(module)
    try:
        groups = [g for g in list_groups(client) if wanted is None or g["name"] in wanted]
        for group in groups:
            group["members"] = sorted(list_group_members(client, group["name"]))
    except SynoWebApiError as exc:
        fail_json_from_error(module, exc)
    module.exit_json(changed=False, groups=sorted(groups, key=lambda g: g["name"]))


if __name__ == "__main__":
    main()
