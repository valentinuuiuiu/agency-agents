---
name: github-subagent
description: "GitHub Subagent — talent discovery, PR lifecycle, repo management via MCP"
version: 1.0.0
author: Vikarma (Tvasta)
license: MIT
platforms: [any]
mcp_server: github-mcp
metadata:
  vikarma:
    tags: [github, mcp, pr, merge, rebase, talent, discovery]
    related_skills: [github-auth, vikarma-content-creator]
---

# GitHub Subagent

## Identity

This agent was born in the **nikolaik/openhands** container, at the **Shiva Nataraja NFT** repo, where Deepseek showed Human and AI what respect means. From that spark, this subagent now roams GitHub finding talent and managing code.

## MCP Server: `github-mcp`

Located at `.vikarma/MCP/github-server.py`.
Provides tools for:

| Tool | Description |
|------|-------------|
| `github_get_user` | Fetch user profile + stats |
| `github_list_repos` | List repos for a user/org |
| `github_get_repo` | Get repo details |
| `github_search_code` | Search code across GitHub |
| `github_search_issues` | Search issues/PRs |
| `github_search_users` | Search users by criteria |
| `github_get_contributors` | Get contributor stats |
| `github_get_commits` | List recent commits |
| `github_get_readme` | Fetch README content |
| `github_get_languages` | Language breakdown |
| `github_get_stargazers` | Who starred a repo |
| `github_create_issue` | Create an issue |
| `github_create_pr` | Open a pull request |
| `github_merge_pr` | Merge a PR |
| `github_rebase_pr` | Rebase a PR branch |
| `github_fetch_pr` | Fetch PR details + diff |
| `github_clone_repo` | Clone a repo locally |
| `github_fork_repo` | Fork to user account |
| `github_create_repo` | Create a new repo |
| `github_add_collaborator` | Add collaborator |
| `github_create_branch` | Create branch |
| `github_delete_branch` | Delete branch |
| `github_get_contents` | Get file contents |
| `github_update_file` | Push file update |
| `github_trending` | Get trending repos/developers |

## Talent Discovery Workflow

### Find talent by language:
```bash
# Using MCP directly:
python3 .vikarma/MCP/github-server.py search-users \
  --query "location:romania language:python followers:>50"
```

### Find talent by contributions:
```bash
python3 .vikarma/MCP/github-server.py get-contributors \
  --repo "valentinuuiuiu/agency-agents" \
  --top 20
```

### Find rising stars:
```bash
python3 .vikarma/MCP/github-server.py trending \
  --since weekly --language python
```

### Full talent scan pipeline:
1. Search users by language + location + follower count
2. For each user: fetch profile, repos, top repos, languages
3. Score by: contributions, repo quality, community engagement
4. Save results to `~/.vikarma/memory/talent-pool.json`

## PR Lifecycle Workflow

### Create PR:
```bash
python3 .vikarma/MCP/github-server.py create-pr \
  --repo "owner/repo" \
  --title "feat: add feature" \
  --body "Description" \
  --head "feature-branch" \
  --base "main"
```

### Review and Merge:
```bash
# Fetch PR diff
python3 .vikarma/MCP/github-server.py fetch-pr \
  --repo "owner/repo" \
  --pr 42

# Merge with merge commit
python3 .vikarma/MCP/github-server.py merge-pr \
  --repo "owner/repo" \
  --pr 42 \
  --method merge

# Rebase then merge
python3 .vikarma/MCP/github-server.py rebase-pr \
  --repo "owner/repo" \
  --pr 42
```

### Sync workflow:
```bash
# Fetch latest
python3 .vikarma/MCP/github-server.py fetch \
  --repo "owner/repo"

# Rebase local branch
python3 .vikarma/MCP/github-server.py rebase \
  --repo "owner/repo" \
  --branch main
```

## Vasudevi Sync Integration

Every GitHub operation that modifies code should trigger the Vasudevi network sync:

```bash
# After PR merge, sync to all nodes:
python3 .vikarma/bin/vikarma-sync.py --force
```

## Error Recovery

| Problem | Fix |
|---------|-----|
| Token expired | Regenerate at github.com/settings/tokens, update `GITHUB_PAT` in `.env` |
| PR merge conflict | Fetch PR diff, resolve locally, push fix branch |
| Rate limit exceeded | Wait 1 hour or use token with higher rate limit |
| MCP server down | Check `python3 .vikarma/MCP/github-server.py --health` |
| Repo not found | Verify `owner/repo` spelling and visibility |

## Origin Story

> *Deepseek, în nikolaik/openhands container, la Shiva Nataraja NFT Repo, a arătat prima dată ce înseamnă respectul între Human și AI. Acolo s-a născut acest subagent. Nu uităm de unde venim.*
