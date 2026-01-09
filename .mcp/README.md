# MCP Server Configuration

This directory contains MCP (Model Context Protocol) server configurations.

## Puppeteer MCP

Used for browser automation and E2E testing.

### Setup

The Puppeteer MCP server will be automatically started when Claude Code detects
the configuration. No manual setup required.

### Requirements

- Node.js 18+ installed
- npx available in PATH

### Configuration

See `puppeteer.json` for the server configuration.

### Environment Variables

- `PUPPETEER_HEADLESS`: Set to `true` for headless mode (default), `false` to see browser

### Usage in Claude Code

Once configured, the following tools become available:

- `mcp__puppeteer__puppeteer_navigate` - Navigate to URL
- `mcp__puppeteer__puppeteer_screenshot` - Take screenshot
- `mcp__puppeteer__puppeteer_click` - Click element
- `mcp__puppeteer__puppeteer_fill` - Fill input field
- `mcp__puppeteer__puppeteer_select` - Select dropdown option
- `mcp__puppeteer__puppeteer_hover` - Hover over element
- `mcp__puppeteer__puppeteer_evaluate` - Execute JavaScript

### Troubleshooting

If Puppeteer MCP isn't working:

1. Check Node.js is installed: `node --version`
2. Check npx is available: `npx --version`
3. Try manual start: `npx -y @anthropic/mcp-server-puppeteer`
4. Check Claude Code MCP settings: `/mcp`
