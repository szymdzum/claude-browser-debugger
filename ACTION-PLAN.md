# Action Plan: Set Up Global, Version-Controlled Skill

This is your step-by-step guide to convert this skill into a globally available, version-controlled tool.

## Decision: Standalone Repo vs Dotfiles

Based on your requirements, **I recommend a standalone repository** because:

| Criterion | Standalone Repo | In Dotfiles | Winner |
|-----------|----------------|-------------|--------|
| Shareable with anyone | ✅ Just clone | ❌ Must extract | **Standalone** |
| Version control | ✅ Own history | ⚠️ Mixed with personal config | **Standalone** |
| GitHub stars/issues | ✅ Yes | ❌ No | **Standalone** |
| Easy updates for others | ✅ `git pull` | ⚠️ Pull entire dotfiles | **Standalone** |
| Separation of concerns | ✅ Tool vs config | ❌ Everything together | **Standalone** |

Your dotfiles (`~/Developer/dotfiles/claude/`) should remain for **personal configuration**:
- `CLAUDE.md` - Your global instructions
- `settings.json` - Your preferences
- `statusline.sh` - Your statusline

The skill should be a **separate tool** that anyone can use, regardless of their dotfiles setup.

## Recommended Steps

### 1. Create Standalone Repository

```bash
# Navigate to your Developer directory
cd ~/Developer

# Create new repository
mkdir claude-browser-debugger
cd claude-browser-debugger

# Initialize git
git init
git branch -M main

# Create initial README
cat > README.md << 'EOF'
# Browser Debugger Skill for Claude Code

Debug websites using Chrome DevTools Protocol. Extract DOM, monitor console logs, and track network requests.

## Installation

'''bash
./install.sh --symlink
'''

See [QUICK-START.md](QUICK-START.md) for usage examples.
EOF

# Initial commit
git add README.md
git commit -m "Initial commit"
```

### 2. Copy Skill Files

```bash
# Still in ~/Developer/claude-browser-debugger
cp ~/Developer/kf-ng-web/.claude/skills/browser-debugger/SKILL.md .
cp ~/Developer/kf-ng-web/.claude/skills/browser-debugger/README.md ./README-SKILL.md
cp ~/Developer/kf-ng-web/.claude/skills/browser-debugger/QUICK-START.md .
cp ~/Developer/kf-ng-web/.claude/skills/browser-debugger/MIGRATION-GUIDE.md .
cp ~/Developer/kf-ng-web/.claude/skills/browser-debugger/install.sh .
cp ~/Developer/kf-ng-web/.claude/skills/browser-debugger/*.py .
cp ~/Developer/kf-ng-web/.claude/skills/browser-debugger/debug-page.sh .

# Make scripts executable
chmod +x install.sh *.py debug-page.sh

# Create .gitignore
cat > .gitignore << 'EOF'
# macOS
.DS_Store

# Python
*.pyc
__pycache__/
*.pyo
*.pyd
.Python

# Logs
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# Test outputs
/tmp/
*.tmp
EOF
```

### 3. Commit Everything

```bash
git add .
git commit -m "Add browser debugger skill

- CDP console monitoring
- CDP network monitoring with optional body capture
- Convenience wrapper script
- Flexible installer supporting symlink and copy modes"
```

### 4. Install Globally

```bash
# Install with symlink mode (recommended)
./install.sh --symlink

# This creates:
# ~/.claude/skills/browser-debugger → ~/Developer/claude-browser-debugger
```

### 5. Verify Installation

```bash
# Check the symlink
ls -la ~/.claude/skills/

# Should show:
# browser-debugger -> /Users/szymondzumak/Developer/claude-browser-debugger

# Verify SKILL.md is accessible
cat ~/.claude/skills/browser-debugger/SKILL.md | head -10

# Test with Claude Code
cd ~/Developer/any-project
claude
# Ask: "Debug https://example.com"
```

### 6. Optional: Push to GitHub

```bash
# Create repository on GitHub first, then:
cd ~/Developer/claude-browser-debugger

git remote add origin git@github.com:YOUR-USERNAME/claude-browser-debugger.git
git push -u origin main

# Optional: Create a release
git tag -a v1.0.0 -m "First stable release"
git push --tags
```

### 7. Clean Up Project-Local Copy

```bash
# Once global installation works, remove from project
rm -rf ~/Developer/kf-ng-web/.claude/skills/browser-debugger

# The skill will still work globally
# Test: cd to kf-ng-web and start claude, ask to debug a page
```

## Alternative: Add to Dotfiles

If you prefer to keep it in dotfiles:

```bash
# Create skills directory in dotfiles
cd ~/Developer/dotfiles
mkdir -p claude/skills

# Copy the skill
cp -r ~/Developer/kf-ng-web/.claude/skills/browser-debugger \
     claude/skills/browser-debugger

# Commit to dotfiles
git add claude/skills/browser-debugger
git commit -m "Add Claude browser debugger skill"
git push

# Install globally via symlink
cd claude/skills/browser-debugger
./install.sh --symlink

# This creates:
# ~/.claude/skills/browser-debugger → ~/Developer/dotfiles/claude/skills/browser-debugger
```

## Usage After Installation

### For You (Developer):

```bash
# Update the skill
cd ~/Developer/claude-browser-debugger
# Make changes...
git add .
git commit -m "Add new feature"
git push

# Changes are immediately available (symlink mode)
# Just restart Claude Code if needed
```

### For Others (Users):

```bash
# Clone your repository
git clone https://github.com/YOUR-USERNAME/claude-browser-debugger.git
cd claude-browser-debugger

# Install
./install.sh --symlink

# Use with Claude Code
claude
# Ask: "Debug https://example.com"

# Update later
git pull
# Changes immediately available (if using symlink mode)
```

## File Structure After Migration

### Your Setup:

```
~/Developer/
├── claude-browser-debugger/          # NEW: Standalone repo
│   ├── .git/
│   ├── README.md
│   ├── SKILL.md
│   ├── QUICK-START.md
│   ├── MIGRATION-GUIDE.md
│   ├── ACTION-PLAN.md
│   ├── install.sh
│   ├── cdp-console.py
│   ├── cdp-network.py
│   ├── cdp-network-with-body.py
│   └── debug-page.sh
│
├── dotfiles/                         # Your personal config
│   └── claude/
│       ├── CLAUDE.md                 # Global instructions
│       ├── settings.json             # Preferences
│       └── statusline.sh             # Statusline
│
└── kf-ng-web/                        # Your projects
    └── (no .claude/skills)           # Uses global skill

~/.claude/
└── skills/
    └── browser-debugger/             # SYMLINK → ~/Developer/claude-browser-debugger
```

### Anyone Else's Setup:

```
~/
├── code/
│   └── claude-browser-debugger/      # Cloned from GitHub
│       ├── .git/
│       └── ...
│
└── .claude/
    └── skills/
        └── browser-debugger/         # SYMLINK → ~/code/claude-browser-debugger
```

## Next Steps Checklist

- [ ] **Step 1**: Create `~/Developer/claude-browser-debugger/` directory
- [ ] **Step 2**: Initialize git repository
- [ ] **Step 3**: Copy all skill files from project
- [ ] **Step 4**: Make scripts executable
- [ ] **Step 5**: Create `.gitignore`
- [ ] **Step 6**: Initial git commit
- [ ] **Step 7**: Run `./install.sh --symlink`
- [ ] **Step 8**: Verify `~/.claude/skills/browser-debugger` symlink
- [ ] **Step 9**: Test with Claude Code
- [ ] **Step 10**: Optional - Create GitHub repository
- [ ] **Step 11**: Optional - Push to GitHub
- [ ] **Step 12**: Remove project-local copy

## Quick Command Summary

```bash
# Full setup in one go:
cd ~/Developer
mkdir claude-browser-debugger
cd claude-browser-debugger
git init
git branch -M main
cp ~/Developer/kf-ng-web/.claude/skills/browser-debugger/* .
chmod +x install.sh *.py debug-page.sh
echo ".DS_Store" > .gitignore
git add .
git commit -m "Initial commit: Browser debugger skill"
./install.sh --symlink
ls -la ~/.claude/skills/
```

## Troubleshooting

### Symlink not working?

```bash
# Check if symlink was created
ls -la ~/.claude/skills/browser-debugger

# If it's a directory instead of symlink, remove and reinstall
rm -rf ~/.claude/skills/browser-debugger
cd ~/Developer/claude-browser-debugger
./install.sh --symlink
```

### Claude doesn't discover the skill?

```bash
# Restart Claude Code (skills loaded at startup)
# Verify SKILL.md has proper YAML frontmatter
cat ~/.claude/skills/browser-debugger/SKILL.md | head -5

# Should show:
# ---
# name: Browser Debugger
# description: ...
# ---
```

### Want to switch between copy and symlink?

```bash
# Switch from copy to symlink
rm -rf ~/.claude/skills/browser-debugger
cd ~/Developer/claude-browser-debugger
./install.sh --symlink

# Switch from symlink to copy
rm ~/.claude/skills/browser-debugger
cd ~/Developer/claude-browser-debugger
./install.sh --copy
```

## Questions?

- **Q: Can I keep both project-local and global?**
  A: Yes, project-local takes precedence. Useful for testing changes.

- **Q: How do I share with my team?**
  A: Push to GitHub, share the URL. They clone and run `./install.sh`.

- **Q: What if I don't want symlink?**
  A: Use `./install.sh --copy` for standalone installation.

- **Q: How do I update the skill?**
  A: With symlink: `git pull` in repo. With copy: `git pull` then `./install.sh --copy`.

## Summary

**Recommended approach:**
1. ✅ Create standalone repository at `~/Developer/claude-browser-debugger`
2. ✅ Install globally with symlink: `./install.sh --symlink`
3. ✅ Push to GitHub for sharing
4. ✅ Keep dotfiles for personal configuration only

This gives you:
- **Version control** - Full git history
- **Easy sharing** - Anyone can clone and install
- **Simple updates** - `git pull` and done
- **Global availability** - Works in all projects
- **Clean separation** - Tools vs personal config
