# Kubiya Workflow SDK Documentation

This directory contains the documentation for the Kubiya Workflow SDK, hosted on [Mintlify Cloud](https://mintlify.com).

## 🚀 Local Development

```bash
# Run the documentation locally
mintlify dev

# Check for broken links
mintlify broken-links
```

The documentation will be available at `http://localhost:3000`.

## 🌐 Deploying to Mintlify Cloud

### Step 1: Push to GitHub

Make sure your `docs/kubiya` directory with the `docs.json` file is pushed to your GitHub repository.

### Step 2: Connect to Mintlify

1. Go to [dash.mintlify.com](https://dash.mintlify.com)
2. Sign in with your GitHub account
3. Click "New Project" or "Add Documentation"
4. Select your repository: `kubiya-ai/workflow_sdk`
5. Set the docs directory path: `docs/kubiya`
6. Choose your subdomain (e.g., `workflow-sdk-docs`)
7. Click "Deploy"

### Step 3: Custom Domain (Optional)

After deployment, you can add a custom domain:
1. Go to your project settings in Mintlify dashboard
2. Navigate to "Custom Domain"
3. Add your domain (e.g., `docs.kubiya.ai`)
4. Update your DNS records as instructed

## 📝 Documentation Structure

```
docs/kubiya/
├── docs.json              # Mintlify configuration
├── assets/               # Images and static files
├── getting-started/      # Getting started guides
├── providers/            # AI provider documentation
├── workflows/            # Workflow documentation
├── servers/              # Server documentation
└── api-reference/        # API documentation
```

## 🔧 Configuration

The documentation is configured via `docs.json`. Key settings:

- **Theme**: `willow` (Mintlify's modern theme)
- **Colors**: Kubiya brand colors
- **Navigation**: Organized by sections
- **Search**: Enabled with custom prompt
- **Social Links**: GitHub,  X

## 📚 Writing Documentation

### File Format
- Use `.mdx` files for documentation pages
- MDX allows you to use React components in Markdown

### Frontmatter
Each page should have frontmatter:
```yaml
---
title: "Page Title"
description: "Page description for SEO"
icon: "icon-name"
---
```

### Components
Mintlify provides many built-in components:
- `<Card>` - Feature cards
- `<CardGroup>` - Group of cards
- `<Tabs>` - Tabbed content
- `<Accordion>` - Collapsible sections
- `<CodeBlock>` - Syntax-highlighted code
- `<Note>`, `<Warning>`, `<Tip>` - Callout boxes

## 🔗 Useful Links

- [Mintlify Documentation](https://mintlify.com/docs)
- [Mintlify Dashboard](https://dash.mintlify.com)
- [Component Library](https://mintlify.com/docs/components)
- [Kubiya Platform](https://compose.kubiya.ai)
