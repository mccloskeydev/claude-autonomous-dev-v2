# Roadmap - Claude Autonomous Development Framework v2

## Planned Improvements

### 1. Metaprompting Approach Rework

**Priority:** High
**Source:** [Stop Telling Claude Code What To Do](https://youtu.be/8_7Sq6Vu0S4?si=z5-96cH_oFFJDGwC) by Tash Teaches

Rework discovery, planning, and other prompt generation to use metaprompting strategy. This approach significantly improves the quality and reliability of AI-generated software by having Claude generate its own prompts based on context rather than following rigid instructions.

**Affected areas:**
- `.claude/skills/discovery/SKILL.md`
- `.claude/skills/plan-alternatives/SKILL.md`
- `.claude/skills/architect/SKILL.md`
- `.claude/skills/build-new-project/SKILL.md`

---

### 2. Plugin Integrations

**Source:** [claude-plugins-official](https://github.com/anthropics/claude-plugins-official/tree/main/plugins)

Integrate official Anthropic plugins into the autonomous workflow:

#### 2.1 code-review
- **Purpose:** Automated code review during implementation
- **Integration point:** After implementation, before QA

#### 2.2 commit-commands
- **Purpose:** Standardized commit message generation
- **Integration point:** TDD cycle commits

#### 2.3 feature-dev
- **Purpose:** Feature development workflow assistance
- **Integration point:** Implementation phase

#### 2.4 frontend-design
- **Purpose:** UI/UX design assistance for web projects
- **Integration point:** Architecture phase (for frontend projects)

#### 2.5 hookify
- **Purpose:** Dynamic hook generation when needed
- **Integration point:** When new automation triggers are required

#### 2.6 plugin-dev
- **Purpose:** Build new plugins as needed
- **Integration point:** When extending framework capabilities

#### 2.7 security-guidance
- **Purpose:** Security best practices and vulnerability detection
- **Integration point:** Code review and evaluation phases

#### 2.8 code-simplifier (Critical)
- **Purpose:** Simplify and refactor code
- **Integration point:** **After implementation, BEFORE QA/testing**
- **Note:** This should be a mandatory step in the workflow

---

## Proposed Workflow Update

After plugin integration, the workflow should become:

```
Discover → Plan → Architect → Implement (TDD) → Simplify → Review → Test → Fix → Verify
                                                    ↑          ↑
                                            code-simplifier  code-review
                                                            security-guidance
```

---

## Implementation Notes

- Each plugin integration should follow TDD
- Update `specs/features.json` when implementation begins
- Plugins should be optional/configurable in `project.config.json`
- Consider creating a plugin loader/manager module

---

## Status

| Item | Status | Notes |
|------|--------|-------|
| Metaprompting rework | Planned | Requires video analysis first |
| code-review | Planned | |
| commit-commands | Planned | |
| feature-dev | Planned | |
| frontend-design | Planned | |
| hookify | Planned | |
| plugin-dev | Planned | |
| security-guidance | Planned | |
| code-simplifier | Planned | High priority - workflow change |
