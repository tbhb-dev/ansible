#!/usr/bin/python
# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

DOCUMENTATION = r"""
module: user_info
short_description: Read the local users of a Synology DSM NAS
version_added: "0.1.0"
description:
  - Lists the local users on a DSM NAS with the groups each belongs to, by running C(synowebapi --exec) on the managed node.
  - Read-only. It changes nothing on the NAS.
  - Needs a user that may run C(synowebapi), which on DSM is root. Use C(become).
  - Synology publishes no guide for these APIs. See the module source for the references and for what is unverified.
options:
  name:
    description:
      - Return only the users with these names.
      - A name that matches no user is left out of the result and is not an error.
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
- name: Read every local user
  tbhb.dsm.user_info:
  become: true
  register: users

- name: Read one user and show their groups
  tbhb.dsm.user_info:
    name: alice
  become: true
  register: alice

- ansible.builtin.debug:
    msg: "{{ alice.users[0].groups }}"
"""

RETURN = r"""
users:
  description: The local users, sorted by name.
  returned: success
  type: list
  elements: dict
  contains:
    name:
      description: The user name.
      type: str
      sample: alice
    uid:
      description: The numeric user ID, when DSM reports it.
      type: int
      sample: 1026
    description:
      description: The user description.
      type: str
      sample: Alice Example
    email:
      description: The user's email address.
      type: str
      sample: alice@example.com
    expired:
      description: DSM's account expiry state, for example C(normal).
      type: str
      sample: normal
    groups:
      description: The names of the groups the user is a member of, sorted.
      type: list
      elements: str
      sample: ["administrators", "users"]
    shell:
      description:
        - The user's login shell when DSM's reply carries one, otherwise V(null).
        - The wrapper this module is modelled on does not show a shell field, so expect V(null) until a real reply confirms one.
      type: str
      sample: /bin/sh
"""

# API references. Synology publishes no guide for SYNO.Core.*. All are cited to
# the community wrapper N4S4/synology-api:
#   SYNO.Core.User          method=list  type=local   (core_user.py user_list)
#       cited; version unverified. The wrapper reads it from the NAS at runtime.
#   SYNO.Core.Group         method=list               (core_group.py get_groups)
#       cited; version unverified.
#   SYNO.Core.Group.Member  method=list  ingroup=true (core_group.py get_users)
#       cited; version unverified.
# Unverified: the "shell" field. No wrapper method shows it, so it is passed
# through when the reply has it and is null otherwise.
# Group membership is built from Group.Member, not from the "groups" value of
# User's "additional" list, so each group costs one call.

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
        data = client.call("SYNO.Core.User", "list", version=1, params={"type": "local", "offset": 0, "limit": -1})
        groups_of = {}
        for group in list_groups(client):
            for member in list_group_members(client, group["name"]):
                groups_of.setdefault(member, []).append(group["name"])
    except SynoWebApiError as exc:
        fail_json_from_error(module, exc)

    users = []
    for entry in data.get("users", []):
        name = entry.get("name")
        if wanted is not None and name not in wanted:
            continue
        users.append(
            {
                "name": name,
                "uid": entry.get("uid"),
                "description": entry.get("description", ""),
                "email": entry.get("email", ""),
                "expired": entry.get("expired"),
                "groups": sorted(groups_of.get(name, [])),
                "shell": entry.get("shell"),
            }
        )
    module.exit_json(changed=False, users=sorted(users, key=lambda u: u["name"]))


if __name__ == "__main__":
    main()
