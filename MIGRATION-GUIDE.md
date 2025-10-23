# Migration Guide: Making This Skill Globally Available

This guide shows how to convert this project-local skill into a globally available, version-controlled skill.

## Architecture Overview

```
BEFORE (Project-local):                  AFTER (Global + Version-controlled):
─────────────────────────                ──────────────────────────────────────

~/Developer/kf-ng-web/                   ~/Developer/
  └── .claude/skills/                      ├── claude-browser-debugger/    ← NEW git repo
      └── browser-debugger/                │   ├── .git/
          ├── SKILL.md                     │   ├── README.md
          └── ...                          │   ├── SKILL.md
                                           │   └── ...
                                           │
                                           └── kf-ng-web/
                                               └── .claude/skills/         ← optional

~/.claude/                               ~/.claude/
  (nothing)                                └── skills/
                                               └── browser-debugger/      ← SYMLINK to repo
```

## Step-by-Step Migration

### 1. Create Standalone Repository

Choose one of these approaches:

#### Option A: New Repository (Recommended)

```bash
# Create new repo for the skill
cd ~/Developer
mkdir claude-browser-debugger
cd claude-browser-debugger

# Initialize git
git init
echo "# Browser Debugger Skill for Claude Code" > README.md
git add README.md
git commit -m "Initial commit"

# Copy files from current location
cp -r ~/Developer/kf-ng-web/.claude/skills/browser-debugger/* .

# Commit the skill
git add .
git commit -m "Add browser debugger skill"

# Optional: Create remote repository
git remote add origin git@github.com:yourusername/claude-browser-debugger.git
git push -u origin main
```

#### Option B: Add to Existing Dotfiles

```bash
# If you want to keep it in your dotfiles
cd ~/Developer/dotfiles
mkdir -p claude/skills/browser-debugger

# Copy files
cp -r ~/Developer/kf-ng-web/.claude/skills/browser-debugger/* \
     claude/skills/browser-debugger/

# Commit to dotfiles
git add claude/skills/browser-debugger
git commit -m "Add Claude browser debugger skill"
git push
```

### 2. Install Globally

#### For Option A (Standalone Repo):

```bash
cd ~/Developer/claude-browser-debugger
./install.sh --symlink
```

This creates:
```
~/.claude/skills/browser-debugger → ~/Developer/claude-browser-debugger
```

#### For Option B (Dotfiles):

```bash
cd ~/Developer/dotfiles/claude/skills/browser-debugger
./install.sh --symlink
```

This creates:
```
~/.claude/skills/browser-debugger → ~/Developer/dotfiles/claude/skills/browser-debugger
```

### 3. Verify Installation

```bash
# Check symlink
ls -la ~/.claude/skills/browser-debugger

# Should show something like:
# browser-debugger -> /Users/you/Developer/claude-browser-debugger

# Test with Claude Code
claude
> Debug https://example.com
```

### 4. Clean Up Project-Local Copy (Optional)

Once the global installation works:

```bash
# Remove from project (skill will still work globally)
rm -rf ~/Developer/kf-ng-web/.claude/skills/browser-debugger

# Or keep both if you want project-specific version
# (project version takes precedence over global)
```

## Installation Modes Explained

### Symlink Mode (Recommended)

```bash
./install.sh --symlink
```

**Pros:**
- ✅ Easy updates: `git pull` in the repo
- ✅ Version-controlled: Changes tracked in git
- ✅ Single source of truth
- ✅ Edit once, available immediately

**Cons:**
- ⚠️ Requires keeping the repo directory
- ⚠️ Breaking symlink if you move the repo

**Use when:** You maintain the skill and want easy updates

### Copy Mode

```bash
./install.sh --copy
```

**Pros:**
- ✅ Standalone: No dependency on source directory
- ✅ Portable: Can delete source after install
- ✅ Stable: No accidental changes

**Cons:**
- ❌ Updates require re-running installer
- ❌ Not version-controlled
- ❌ Multiple copies get out of sync

**Use when:** You want a stable, standalone installation

## Updating the Skill

### With Symlink Installation:

```bash
# Navigate to repo
cd ~/Developer/claude-browser-debugger

# Pull latest changes
git pull

# Changes are immediately available in Claude
# (restart Claude if necessary)
```

### With Copy Installation:

```bash
# Navigate to repo
cd ~/Developer/claude-browser-debugger

# Pull latest changes
git pull

# Re-run installer
./install.sh --copy
```

## Sharing with Others

### Option 1: Public GitHub Repository

```bash
# Create repo on GitHub, then:
cd ~/Developer/claude-browser-debugger
git remote add origin git@github.com:yourusername/claude-browser-debugger.git
git push -u origin main
```

Others can install:
```bash
# Clone
git clone https://github.com/yourusername/claude-browser-debugger.git
cd claude-browser-debugger

# Install
./install.sh --symlink
```

### Option 2: Direct Download

Share the directory as a ZIP file. Users can:

```bash
# Extract
unzip claude-browser-debugger.zip
cd claude-browser-debugger

# Install
./install.sh --copy  # Use copy mode since no git repo
```

## Directory Structure Comparison

### Recommended: Standalone Repository

```
~/Developer/
├── claude-browser-debugger/          ← Own git repo
│   ├── .git/
│   ├── .gitignore
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── LICENSE
│   ├── MIGRATION-GUIDE.md           ← This file
│   ├── install.sh
│   ├── SKILL.md
│   ├── QUICK-START.md
│   ├── cdp-console.py
│   ├── cdp-network.py
│   ├── cdp-network-with-body.py
│   └── debug-page.sh
│
├── dotfiles/                         ← Separate from skill
│   └── claude/
│       ├── CLAUDE.md
│       ├── settings.json
│       └── statusline.sh
│
└── kf-ng-web/                        ← Projects don't need the skill
    └── (no .claude/skills)

~/.claude/
└── skills/
    └── browser-debugger/             ← Symlink to repo
```

### Alternative: In Dotfiles

```
~/Developer/
├── dotfiles/                         ← Everything in dotfiles
│   ├── claude/
│   │   ├── CLAUDE.md
│   │   ├── settings.json
│   │   ├── statusline.sh
│   │   └── skills/
│   │       └── browser-debugger/
│   │           ├── install.sh
│   │           └── ...
│   └── install.sh                    ← Dotfiles installer
│
└── kf-ng-web/

~/.claude/
└── skills/
    └── browser-debugger/             ← Symlink to dotfiles/claude/skills/browser-debugger
```

## Best Practices

### 1. Use Standalone Repository When:
- ✅ Skill is useful to multiple people
- ✅ You want GitHub issues/stars
- ✅ Skill evolves independently of personal config
- ✅ You want to share it publicly

### 2. Use Dotfiles When:
- ✅ Skill is highly personalized
- ✅ You want everything in one repo
- ✅ Skill is tightly coupled to your workflow
- ✅ Not sharing with others

### 3. Version Control Tips:

```bash
# Add a .gitignore
cat > .gitignore << 'EOF'
.DS_Store
*.pyc
__pycache__/
*.log
.vscode/
EOF

# Use semantic versioning in tags
git tag -a v1.0.0 -m "Initial stable release"
git push --tags

# Keep a CHANGELOG.md
echo "# Changelog" > CHANGELOG.md
```

### 4. Documentation:

Create a comprehensive README.md with:
- Installation instructions
- Prerequisites
- Usage examples
- Troubleshooting
- Contributing guidelines

## Troubleshooting

### Symlink broken after moving repo

```bash
# Remove old symlink
rm ~/.claude/skills/browser-debugger

# Create new symlink with updated path
cd /new/path/to/claude-browser-debugger
./install.sh --symlink
```

### Skill not discovered by Claude

```bash
# Verify installation
ls -la ~/.claude/skills/browser-debugger

# Check if SKILL.md exists
cat ~/.claude/skills/browser-debugger/SKILL.md | head -5

# Restart Claude Code
# Skills are loaded at startup
```

### Multiple installations conflict

```bash
# Check all locations
ls -la ~/Developer/kf-ng-web/.claude/skills/browser-debugger  # Project
ls -la ~/.claude/skills/browser-debugger                      # Global

# Project skills take precedence
# Remove project version to use global:
rm -rf ~/Developer/kf-ng-web/.claude/skills/browser-debugger
```

## FAQ

**Q: Can I have both project-local and global versions?**
A: Yes. Project-local skills in `.claude/skills/` take precedence over `~/.claude/skills/`.

**Q: How do I uninstall?**
A: `rm -rf ~/.claude/skills/browser-debugger`

**Q: Can I symlink from dotfiles?**
A: Yes, if your dotfiles are version-controlled and you use the symlink approach, you get the benefits of both.

**Q: Does the skill work without git?**
A: Yes, use `--copy` mode. Git is only needed for version control and easy updates.

**Q: How do I contribute changes back?**
A: Fork the repo, make changes, test locally, and submit a pull request.

## Summary

**Recommended Setup:**
```bash
# 1. Create standalone repo
cd ~/Developer
mkdir claude-browser-debugger
cd claude-browser-debugger
git init

# 2. Copy skill files
cp -r ~/Developer/kf-ng-web/.claude/skills/browser-debugger/* .

# 3. Install globally with symlink
./install.sh --symlink

# 4. Optional: Remove from project
rm -rf ~/Developer/kf-ng-web/.claude/skills/browser-debugger
```

This gives you:
- ✅ Global availability
- ✅ Version control
- ✅ Easy sharing
- ✅ Simple updates
- ✅ Clean separation of concerns
