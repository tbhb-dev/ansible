# Agent instructions

## What this is

`tbhb-dev/ansible` holds our own Ansible collections for UniFi and Synology DSM. They live under the `tbhb` namespace, so a module is `tbhb.<collection>.<module>`. The modules are tested against fake APIs, never a live controller or NAS. The repository is public and Apache-2.0 licensed.

## Standing rules

- Nothing private goes in this repository: no hostnames, IP addresses, tailnet names, vault names, or internal repository names. Fixtures and examples use reserved example values.
- Secrets never appear in the tree, in a commit or in a pull request. Examples take credentials as module parameters and show placeholders only.
- Keep private values in an ignored file, never in the tree.

## Commits and pull requests

- Branch first, and change only the files the task needs. Stage paths by name.
- Commit or push only when the operator approves it in your session. Push only to a branch, never to `main`; `main` takes changes by pull request only.
- Use Conventional Commits and a plain `git commit`. Never add `Signed-off-by` or `Co-authored-by`: the operator adds their own sign-off.
- Sign every commit, because `main` requires signed commits. Never pass `-c commit.gpgsign=false` or `--no-gpg-sign`.
- Draft the pull request in `.github/PULL_REQUEST_DRAFT.md`, which git ignores, and fill every section of `.github/PULL_REQUEST_TEMPLATE.md` that applies. Never write the `Generated-by` or `Assisted-by` trailers yourself.
- Write each Markdown paragraph on one line.
- Put agent worktrees in `.worktrees/`, which git ignores.
