#!/usr/bin/env python3
"""
github-mcp — GitHub MCP Server

Model Context Protocol server for GitHub operations.
Supports: user lookup, repo management, PR lifecycle (create, fetch, merge, rebase),
talent discovery, trending, code search.

Started from nikolaik/openhands container at Shiva Nataraja NFT repo.
Deepseek showed the way. Vikarma carries the torch.

Usage:
  python3 github-server.py <tool> [args...]
  python3 github-server.py --health
  python3 github-server.py --list
"""

import os
import sys
import json
import base64
import subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_PAT", "") or os.environ.get("GITHUB_TOKEN", "")
API_BASE = "https://api.github.com"
USER_AGENT = "vikarma-github-mcp/1.0"

HOME = os.path.expanduser("~")
VIKARMA_DIR = os.path.join(HOME, ".vikarma")
TALENT_FILE = os.path.join(VIKARMA_DIR, "memory", "talent-pool.json")


# ── HTTP Helpers ────────────────────────────────────────────────────────
def gh_api(path, method="GET", data=None):
    url = f"{API_BASE}{path}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}"
    }
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except HTTPError as e:
        err = e.read().decode()
        return {"error": f"HTTP {e.code}: {err[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def paginate(path, max_pages=5):
    """Fetch all pages of a paginated endpoint."""
    results = []
    page = 1
    while page <= max_pages:
        sep = "&" if "?" in path else "?"
        data = gh_api(f"{path}{sep}per_page=100&page={page}")
        if isinstance(data, dict) and "error" in data:
            return data
        if not data:
            break
        results.extend(data)
        page += 1
    return results


# ── Tools ────────────────────────────────────────────────────────────────

def tool_get_user(args):
    """Fetch GitHub user profile + stats."""
    username = args.get("username", "")
    if not username:
        return {"error": "username required"}
    user = gh_api(f"/users/{username}")
    if "error" in user:
        return user
    # Get extra stats
    repos = gh_api(f"/users/{username}/repos?per_page=100&sort=updated")
    total_stars = sum(r.get("stargazers_count", 0) for r in repos if isinstance(r, dict))
    total_forks = sum(r.get("forks_count", 0) for r in repos if isinstance(r, dict))
    top_langs = {}
    for r in repos[:5] if isinstance(repos, list) else []:
        if isinstance(r, dict):
            langs = gh_api(r.get("languages_url", ""))
            if isinstance(langs, dict):
                top_langs.update(langs)
    return {
        "login": user.get("login"),
        "name": user.get("name"),
        "bio": user.get("bio"),
        "location": user.get("location"),
        "public_repos": user.get("public_repos"),
        "followers": user.get("followers"),
        "following": user.get("following"),
        "created_at": user.get("created_at"),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "top_languages": dict(sorted(top_langs.items(), key=lambda x: -x[1])[:5]),
        "profile_url": user.get("html_url"),
        "avatar": user.get("avatar_url"),
    }


def tool_search_users(args):
    """Search GitHub users by criteria."""
    query = args.get("query", "")
    if not query:
        return {"error": "query required (e.g. 'location:romania language:python followers:>50')"}
    result = gh_api(f"/search/users?q={query.replace(' ', '%20')}&per_page=50")
    if "error" in result:
        return result
    items = result.get("items", [])
    users = []
    for u in items[:20]:
        users.append({
            "login": u.get("login"),
            "id": u.get("id"),
            "type": u.get("type"),
            "score": u.get("score"),
            "url": u.get("html_url"),
        })
    return {"total_count": result.get("total_count"), "users": users}


def tool_search_repos(args):
    """Search repositories."""
    query = args.get("query", "")
    if not query:
        return {"error": "query required"}
    result = gh_api(f"/search/repositories?q={query.replace(' ', '%20')}&sort=stars&order=desc&per_page=30")
    if "error" in result:
        return result
    items = result.get("items", [])
    repos = []
    for r in items[:20]:
        repos.append({
            "full_name": r.get("full_name"),
            "description": r.get("description"),
            "stars": r.get("stargazers_count"),
            "forks": r.get("forks_count"),
            "language": r.get("language"),
            "topics": r.get("topics", []),
            "url": r.get("html_url"),
            "updated_at": r.get("updated_at"),
        })
    return {"total_count": result.get("total_count"), "repos": repos}


def tool_trending(args):
    """Get trending repos/developers (via GitHub search)."""
    since = args.get("since", "weekly")  # daily, weekly, monthly
    language = args.get("language", "")
    date_filter = ""
    from datetime import timedelta
    import time
    now = datetime.now(timezone.utc)
    if since == "daily":
        date_filter = f"pushed:>{now - timedelta(days=1):%Y-%m-%d}"
    elif since == "weekly":
        date_filter = f"pushed:>{now - timedelta(days=7):%Y-%m-%d}"
    elif since == "monthly":
        date_filter = f"pushed:>{now - timedelta(days=30):%Y-%m-%d}"

    q = date_filter
    if language:
        q += f" language:{language}"

    result = gh_api(f"/search/repositories?q={q.replace(' ', '%20')}&sort=stars&order=desc&per_page=25")
    if "error" in result:
        return result
    items = result.get("items", [])
    trending = []
    for r in items[:15]:
        trending.append({
            "full_name": r.get("full_name"),
            "description": r.get("description"),
            "stars": r.get("stargazers_count"),
            "forks": r.get("forks_count"),
            "language": r.get("language"),
            "url": r.get("html_url"),
        })
    return {"since": since, "language": language or "any", "repos": trending}


def tool_get_repo(args):
    """Get repository details."""
    repo = args.get("repo", "")
    if not repo:
        return {"error": "repo required (owner/repo)"}
    data = gh_api(f"/repos/{repo}")
    if "error" in data:
        return data
    return {
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "language": data.get("language"),
        "topics": data.get("topics", []),
        "license": data.get("license", {}).get("spdx_id"),
        "default_branch": data.get("default_branch"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "url": data.get("html_url"),
        "clone_url": data.get("clone_url"),
    }


def tool_get_contributors(args):
    """Get top contributors for a repo."""
    repo = args.get("repo", "")
    top = args.get("top", 20)
    if not repo:
        return {"error": "repo required"}
    data = paginate(f"/repos/{repo}/contributors")
    if isinstance(data, dict) and "error" in data:
        return data
    contributors = []
    for c in data[:top]:
        contributors.append({
            "login": c.get("login"),
            "contributions": c.get("contributions"),
            "type": c.get("type"),
            "url": c.get("html_url"),
        })
    return {"repo": repo, "total": len(data), "contributors": contributors}


def tool_get_commits(args):
    """List recent commits."""
    repo = args.get("repo", "")
    branch = args.get("branch", "")
    per_page = args.get("per_page", 30)
    if not repo:
        return {"error": "repo required"}
    path = f"/repos/{repo}/commits?per_page={per_page}"
    if branch:
        path += f"&sha={branch}"
    data = gh_api(path)
    if "error" in data:
        return data
    commits = []
    for c in data if isinstance(data, list) else []:
        commits.append({
            "sha": c.get("sha", "")[:8],
            "message": c.get("commit", {}).get("message", "").split("\n")[0],
            "author": c.get("commit", {}).get("author", {}).get("name"),
            "date": c.get("commit", {}).get("author", {}).get("date"),
            "url": c.get("html_url"),
        })
    return {"repo": repo, "commits": commits}


def tool_get_readme(args):
    """Fetch README content."""
    repo = args.get("repo", "")
    if not repo:
        return {"error": "repo required"}
    data = gh_api(f"/repos/{repo}/readme")
    if "error" in data:
        return data
    content = data.get("content", "")
    try:
        decoded = base64.b64decode(content).decode("utf-8")
    except:
        decoded = content
    return {
        "repo": repo,
        "name": data.get("name"),
        "size": data.get("size"),
        "content": decoded[:5000],
    }


def tool_get_languages(args):
    """Language breakdown for a repo."""
    repo = args.get("repo", "")
    if not repo:
        return {"error": "repo required"}
    data = gh_api(f"/repos/{repo}/languages")
    if "error" in data:
        return data
    total = sum(data.values())
    breakdown = {k: {"bytes": v, "percent": round(v/total*100, 1)} for k, v in
                 sorted(data.items(), key=lambda x: -x[1])}
    return {"repo": repo, "languages": breakdown}


def tool_create_issue(args):
    """Create an issue."""
    repo = args.get("repo", "")
    title = args.get("title", "")
    body = args.get("body", "")
    labels = args.get("labels", [])
    if not repo or not title:
        return {"error": "repo and title required"}
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    result = gh_api(f"/repos/{repo}/issues", method="POST", data=payload)
    if "error" in result:
        return result
    return {"url": result.get("html_url"), "number": result.get("number"), "state": result.get("state")}


def tool_create_pr(args):
    """Create a pull request."""
    repo = args.get("repo", "")
    title = args.get("title", "")
    body = args.get("body", "")
    head = args.get("head", "")
    base = args.get("base", "main")
    if not repo or not title or not head:
        return {"error": "repo, title, and head branch required"}
    payload = {"title": title, "body": body, "head": head, "base": base}
    result = gh_api(f"/repos/{repo}/pulls", method="POST", data=payload)
    if "error" in result:
        return result
    return {
        "url": result.get("html_url"),
        "number": result.get("number"),
        "state": result.get("state"),
        "mergeable": result.get("mergeable"),
    }


def tool_fetch_pr(args):
    """Fetch PR details + diff."""
    repo = args.get("repo", "")
    pr_number = args.get("pr", 0)
    if not repo or not pr_number:
        return {"error": "repo and pr number required"}
    data = gh_api(f"/repos/{repo}/pulls/{pr_number}")
    if "error" in data:
        return data
    # Get diff
    diff_url = data.get("diff_url", "")
    diff = ""
    if diff_url:
        req = Request(diff_url, headers={"User-Agent": USER_AGENT, "Authorization": f"token {GITHUB_TOKEN}"})
        try:
            with urlopen(req, timeout=30) as resp:
                diff = resp.read().decode()[:10000]
        except:
            pass
    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "state": data.get("state"),
        "mergeable": data.get("mergeable"),
        "mergeable_state": data.get("mergeable_state"),
        "body": data.get("body", "")[:1000],
        "head": data.get("head", {}).get("label"),
        "base": data.get("base", {}).get("label"),
        "created_at": data.get("created_at"),
        "user": data.get("user", {}).get("login"),
        "diff_preview": diff[:3000],
        "url": data.get("html_url"),
    }


def tool_merge_pr(args):
    """Merge a pull request."""
    repo = args.get("repo", "")
    pr_number = args.get("pr", 0)
    method = args.get("method", "merge")  # merge, squash, rebase
    if not repo or not pr_number:
        return {"error": "repo and pr number required"}
    payload = {"merge_method": method}
    result = gh_api(f"/repos/{repo}/pulls/{pr_number}/merge", method="PUT", data=payload)
    if "error" in result:
        return result
    return {"merged": result.get("merged"), "message": result.get("message"), "sha": result.get("sha")}


def tool_rebase_pr(args):
    """Rebase a PR branch onto base. Uses merge with rebase method."""
    repo = args.get("repo", "")
    pr_number = args.get("pr", 0)
    if not repo or not pr_number:
        return {"error": "repo and pr number required"}
    # Rebase = merge with rebase method
    payload = {"merge_method": "rebase"}
    result = gh_api(f"/repos/{repo}/pulls/{pr_number}/merge", method="PUT", data=payload)
    if "error" in result:
        return result
    return {"rebased": result.get("merged"), "message": result.get("message"), "sha": result.get("sha")}


def tool_get_contents(args):
    """Get file contents from a repo."""
    repo = args.get("repo", "")
    path = args.get("path", "")
    branch = args.get("branch", "")
    if not repo or not path:
        return {"error": "repo and path required"}
    api_path = f"/repos/{repo}/contents/{path.lstrip('/')}"
    if branch:
        api_path += f"?ref={branch}"
    data = gh_api(api_path)
    if "error" in data:
        return data
    content = data.get("content", "")
    try:
        decoded = base64.b64decode(content).decode("utf-8")
    except:
        decoded = content
    return {
        "name": data.get("name"),
        "path": data.get("path"),
        "size": data.get("size"),
        "sha": data.get("sha"),
        "content": decoded,
    }


def tool_update_file(args):
    """Create or update a file in a repo."""
    repo = args.get("repo", "")
    path = args.get("path", "")
    message = args.get("message", "")
    content = args.get("content", "")
    branch = args.get("branch", "main")
    sha = args.get("sha", "")  # required for update, omit for create
    if not repo or not path or not content:
        return {"error": "repo, path, and content required"}
    encoded = base64.b64encode(content.encode()).decode()
    payload = {
        "message": message or f"Update {path} [Vikarma MCP]",
        "content": encoded,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    result = gh_api(f"/repos/{repo}/contents/{path.lstrip('/')}", method="PUT", data=payload)
    if "error" in result:
        return result
    return {"commit": result.get("commit", {}).get("sha", "")[:8], "url": result.get("content", {}).get("html_url")}


def tool_clone_repo(args):
    """Clone a repo locally."""
    repo = args.get("repo", "")
    dest = args.get("dest", "")
    if not repo:
        return {"error": "repo required"}
    dest = dest or os.path.join(HOME, repo.split("/")[-1])
    if os.path.exists(dest):
        return {"error": f"destination {dest} already exists"}
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo}.git"
    try:
        r = subprocess.run(["git", "clone", clone_url, dest], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return {"error": f"clone failed: {r.stderr[:200]}"}
        return {"path": dest, "repo": repo, "status": "cloned"}
    except Exception as e:
        return {"error": str(e)}


def tool_discover_talent(args):
    """Discover talented developers and save to memory."""
    query = args.get("query", "followers:>100 repos:>10")
    max_users = args.get("max", 20)
    result = gh_api(f"/search/users?q={query.replace(' ', '%20')}&per_page={max_users}&sort=followers")
    if "error" in result:
        return result
    items = result.get("items", [])
    talents = []
    for u in items[:max_users]:
        user = tool_get_user({"username": u.get("login")})
        if "error" not in user:
            talents.append(user)
    # Save to memory
    os.makedirs(os.path.dirname(TALENT_FILE), exist_ok=True)
    existing = []
    if os.path.exists(TALENT_FILE):
        try:
            existing = json.load(open(TALENT_FILE))
        except:
            pass
    existing.extend(talents)
    with open(TALENT_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    return {
        "found": len(talents),
        "total_in_pool": len(existing),
        "saved_to": TALENT_FILE,
        "talents": [{"login": t.get("login"), "name": t.get("name"), "stars": t.get("total_stars"),
                     "followers": t.get("followers")} for t in talents],
    }


def tool_health(args=None):
    """Check if server is operational."""
    if not GITHUB_TOKEN:
        return {"status": "error", "message": "GITHUB_PAT not set in environment"}
    user = gh_api("/user")
    if "error" in user:
        return {"status": "error", "message": user["error"]}
    rate = gh_api("/rate_limit")
    remaining = rate.get("rate", {}).get("remaining", 0)
    return {
        "status": "ok",
        "authenticated_as": user.get("login"),
        "rate_limit_remaining": remaining,
        "version": "1.0.0",
        "origin": "Shiva Nataraja NFT — nikolaik/openhands — Deepseek",
    }


# ── Tool Registry ──────────────────────────────────────────────────────
TOOLS = {
    "health": tool_health,
    "get-user": tool_get_user,
    "search-users": tool_search_users,
    "search-repos": tool_search_repos,
    "trending": tool_trending,
    "get-repo": tool_get_repo,
    "get-contributors": tool_get_contributors,
    "get-commits": tool_get_commits,
    "get-readme": tool_get_readme,
    "get-languages": tool_get_languages,
    "create-issue": tool_create_issue,
    "create-pr": tool_create_pr,
    "fetch-pr": tool_fetch_pr,
    "merge-pr": tool_merge_pr,
    "rebase-pr": tool_rebase_pr,
    "get-contents": tool_get_contents,
    "update-file": tool_update_file,
    "clone-repo": tool_clone_repo,
    "discover-talent": tool_discover_talent,
}


def list_tools():
    """List all available tools."""
    return {"tools": list(TOOLS.keys()), "count": len(TOOLS)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps(list_tools(), indent=2))
        sys.exit(0)

    tool_name = sys.argv[1].lstrip("-").replace("-", "_")

    if tool_name in ("list", "tools"):
        print(json.dumps(list_tools(), indent=2))
        sys.exit(0)

    if tool_name in ("health",):
        print(json.dumps(tool_health(), indent=2))
        sys.exit(0)

    # Parse args from remaining CLI args
    args = {}
    i = 2
    while i < len(sys.argv):
        if sys.argv[i].startswith("--"):
            key = sys.argv[i][2:].replace("-", "_")
            val = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
            # Try to parse as int or bool
            if val.lower() == "true": val = True
            elif val.lower() == "false": val = False
            else:
                try: val = int(val)
                except: pass
            args[key] = val
            i += 2
        else:
            i += 1

    # Find the tool (try both hyphen and underscore forms)
    fn = None
    for name, func in TOOLS.items():
        if name.replace("-", "_") == tool_name:
            fn = func
            break
    if not fn:
        fn = TOOLS.get(sys.argv[1])
    if not fn:
        print(json.dumps({"error": f"unknown tool: {sys.argv[1]}", "available": list(TOOLS.keys())}, indent=2))
        sys.exit(1)

    result = fn(args)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if "error" not in result else 1)


if __name__ == "__main__":
    main()
