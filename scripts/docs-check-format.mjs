#!/usr/bin/env node
/**
 * scene-fab docs markdown format checker
 *
 * Checks:
 * 1. H1 count (should be exactly 1 per file, excluding code blocks)
 * 2. Code block language tags (should be present)
 * 3. Heading underline style consistency (--- vs ===)
 * 4. Trailing whitespace
 */

import { readdirSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DOCS_DIR = join(__dirname, '..', 'docs');

function checkFile(filePath) {
  const content = readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const issues = [];
  const relPath = filePath.replace(process.cwd() + '/', '');

  // Remove code blocks before checking
  const nonCodeLines = [];
  let inCodeBlock = false;
  for (const line of lines) {
    if (line.trim().startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (!inCodeBlock) {
      nonCodeLines.push(line);
    }
  }

  // 1. Check H1 count (should be exactly 1, excluding code blocks)
  const h1Count = nonCodeLines.filter(line => line.startsWith('# ')).length;
  if (h1Count !== 1) {
    issues.push(`H1 count: ${h1Count} (expected 1)`);
  }

  // 2. Check code blocks have language tags
  let inCode = false;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim().startsWith('```')) {
      inCode = !inCode;
      if (inCode) {
        const lang = lines[i].slice(3).trim();
        if (!lang) {
          issues.push(`Line ${i + 1}: Empty code block language tag`);
        }
      }
    }
  }

  // 3. Check heading underline style (only --- allowed, not ===)
  for (let i = 0; i < nonCodeLines.length; i++) {
    const line = nonCodeLines[i];
    if (line.startsWith('# ') && i + 1 < nonCodeLines.length) {
      const underline = nonCodeLines[i + 1].trim();
      if (underline === '===') {
        issues.push(`Line ${i + 1}: Use ## instead of === underline`);
      }
    }
  }

  // 4. Check trailing whitespace
  const trailingWs = lines.filter(line => line !== line.trimEnd()).length;
  if (trailingWs > 0) {
    issues.push(`${trailingWs} lines with trailing whitespace`);
  }

  return issues;
}

function walk(dir) {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
      files.push(...walk(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      files.push(fullPath);
    }
  }
  return files;
}

const files = walk(DOCS_DIR).filter(f => !f.endsWith('docs/index.md'));
let totalIssues = 0;

console.log(`📚 Checking ${files.length} markdown files in docs/...`);

for (const file of files) {
  const issues = checkFile(file);
  if (issues.length > 0) {
    const relPath = file.replace(process.cwd() + '/', '');
    console.log(`\n⚠️  ${relPath}:`);
    for (const issue of issues) {
      console.log(`   - ${issue}`);
    }
    totalIssues += issues.length;
  }
}

if (totalIssues === 0) {
  console.log('✅ All files passed format checks!');
  process.exit(0);
} else {
  console.log(`\n❌ Found ${totalIssues} issues in ${files.filter(f => checkFile(f).length > 0).length} files`);
  process.exit(1);
}
