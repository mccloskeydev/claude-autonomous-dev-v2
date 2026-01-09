---
name: test-e2e
description: |
  End-to-end browser testing with Puppeteer. Use when: "e2e test", "browser test", "functional test",
  "test UI", "verify in browser". Tests real user flows via browser automation.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - mcp__puppeteer__puppeteer_navigate
  - mcp__puppeteer__puppeteer_screenshot
  - mcp__puppeteer__puppeteer_click
  - mcp__puppeteer__puppeteer_fill
  - mcp__puppeteer__puppeteer_select
  - mcp__puppeteer__puppeteer_hover
  - mcp__puppeteer__puppeteer_evaluate
---

# End-to-End Browser Testing

Test user-facing features through browser automation.

## Input
`$ARGUMENTS` - Feature to test, or "all" for full E2E suite

## Prerequisites

1. **Dev server running** - Check project.config.json for dev_server_command
2. **Puppeteer MCP available** - Tools like mcp__puppeteer__* should be accessible

## Process

### Step 1: Start Dev Server (if needed)

Check if server is running:
```bash
curl -s http://localhost:3000 > /dev/null && echo "Server running" || echo "Server not running"
```

If not running, start it (in background):
```bash
# Read command from project.config.json
# Example: bun run dev &
```

### Step 2: Define Test Scenarios

For the feature, identify user flows:

```markdown
## Feature: User Login

### Scenario 1: Successful login
1. Navigate to /login
2. Fill email field with "test@example.com"
3. Fill password field with "password123"
4. Click "Login" button
5. Verify redirected to /dashboard
6. Verify user name displayed

### Scenario 2: Invalid credentials
1. Navigate to /login
2. Fill email with "wrong@example.com"
3. Fill password with "wrongpass"
4. Click "Login"
5. Verify error message displayed
6. Verify still on /login page
```

### Step 3: Execute Tests

For each scenario, use Puppeteer MCP tools:

#### Navigate to page
```
mcp__puppeteer__puppeteer_navigate
url: "http://localhost:3000/login"
```

#### Take screenshot for verification
```
mcp__puppeteer__puppeteer_screenshot
name: "login-page-initial"
```

#### Fill form fields
```
mcp__puppeteer__puppeteer_fill
selector: "input[name='email']"
value: "test@example.com"
```

#### Click buttons
```
mcp__puppeteer__puppeteer_click
selector: "button[type='submit']"
```

#### Evaluate page state
```
mcp__puppeteer__puppeteer_evaluate
script: "document.querySelector('.user-name')?.textContent"
```

### Step 4: Verify Results

After each action, verify expected state:
- Take screenshots at key points
- Evaluate DOM for expected elements
- Check URL for navigation
- Look for error messages

### Step 5: Document Results

Create/update test results:

```markdown
# E2E Test Results

## Feature: User Login
Tested: 2026-01-09T12:00:00Z

### Scenario 1: Successful login
- Status: PASS
- Screenshots: [login-initial.png, login-success.png]

### Scenario 2: Invalid credentials
- Status: PASS
- Screenshots: [login-error.png]

## Feature: Dashboard
...
```

Save to: specs/e2e-results.md

### Step 6: Handle Failures

If a test fails:

1. **Screenshot the failure state**
2. **Log to specs/bugs.md**:
```markdown
## Bug: Login redirect fails

**Found:** E2E test - Scenario 1, Step 5
**Expected:** Redirect to /dashboard
**Actual:** Stays on /login, no error shown
**Screenshot:** e2e-login-fail.png
**Priority:** High
```

3. **Continue with other tests** - Don't block on one failure

## Common Selectors

```javascript
// Forms
"input[name='email']"
"input[type='password']"
"button[type='submit']"
"form#login-form"

// Navigation
"a[href='/dashboard']"
"nav .menu-item"
"button.logout"

// Content
".error-message"
".success-message"
"h1.page-title"
"[data-testid='user-name']"
```

## Tips

1. **Use data-testid attributes** for reliable selectors
2. **Wait for navigation** after clicks that change pages
3. **Screenshot before and after** actions for debugging
4. **Test both happy and sad paths**
5. **Check mobile viewport** if responsive

## Output

1. E2E test results in specs/e2e-results.md
2. Screenshots in specs/screenshots/
3. Any bugs logged to specs/bugs.md
4. Entry in specs/progress.md
