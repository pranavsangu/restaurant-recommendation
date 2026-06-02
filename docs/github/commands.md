# GitHub Commands Reference

This file records the Git/GitHub commands used to prepare this project for upload.

---

## Repository Setup

Initialized the local repository:

```bash
git init -b main
```

Checked ignored files and worktree status:

```bash
git status --short --ignored
git check-ignore -v .env .cache/zomato/restaurants.normalized.jsonl src/zomato_ai_recommendations.egg-info/PKG-INFO
```

Confirmed these local/sensitive artifacts are ignored:

- `.env`
- `.cache/`
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `*.egg-info/`

---

## Initial Commit

Staged project files:

```bash
git add .
```

Created the initial commit:

```bash
git commit -m "Initial Zomato AI recommendation app"
```

Latest known initial commit:

```text
3c03a4b Initial Zomato AI recommendation app
```

---

## GitHub Remote

Added GitHub remote:

```bash
git remote add origin https://github.com/pranavsangu/restaurant-recommendation.git
```

Checked remote:

```bash
git remote -v
```

---

## Push Attempt

Attempted to push:

```bash
git push -u origin main
```

The push failed because the GitHub repository did not exist yet:

```text
remote: Repository not found.
fatal: repository 'https://github.com/pranavsangu/restaurant-recommendation.git/' not found
```

---

## Next Steps

Create the repository on GitHub first:

```text
Owner: pranavsangu
Repository name: restaurant-recommendation
URL: https://github.com/pranavsangu/restaurant-recommendation.git
```

Do not initialize it with README, `.gitignore`, or license because this project already has local files and an initial commit.

After the repo exists, push again:

```bash
git push -u origin main
```

---

## Useful Follow-Up Commands

Check current branch:

```bash
git branch
```

Check current status:

```bash
git status
```

Check latest commit:

```bash
git log --oneline -1
```

Change remote URL if needed:

```bash
git remote set-url origin https://github.com/pranavsangu/restaurant-recommendation.git
```

Push future commits:

```bash
git push
```
