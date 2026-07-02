#!/usr/bin/env node
/**
 * scene-fab docs external link checker
 *
 * Scans docs/ for all external HTTP(S) links and verifies they return 2xx/3xx.
 * Excludes:
 *   - Local/internal links
 *   - Anchor links
 *   - mailto:/tel: links
 *   - localhost / 127.0.0.1
 */

import { readdirSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DOCS_DIR = join(__dirname, '..', 'docs');
const TIMEOUT_MS = 10000;
const CONCURRENCY = 5;

const SKIP_DOMAINS = [
  'github.com/Agions/scene-fab', // self
];

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

function extractLinks(content) {
  const links = new Set();
  const regex = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g;
  let match;
  while ((match = regex.exec(content)) !== null) {
    links.add(match[2]);
  }
  return Array.from(links);
}

async function checkLink(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      method: 'HEAD',
      redirect: 'follow',
      signal: controller.signal,
      headers: { 'User-Agent': 'scene-fab-docs-link-checker/1.0' },
    });
    clearTimeout(timeout);
    return { url, status: response.status, ok: response.ok || (response.status >= 300 && response.status < 400) };
  } catch (err) {
    clearTimeout(timeout);
    return { url, status: 0, ok: false, error: err.message };
  }
}

async function main() {
  const files = walk(DOCS_DIR);
  const allLinks = new Set();
  const linkToFiles = new Map();

  for (const file of files) {
    const content = readFileSync(file, 'utf-8');
    const links = extractLinks(content);
    for (const link of links) {
      allLinks.add(link);
      if (!linkToFiles.has(link)) {
        linkToFiles.set(link, []);
      }
      linkToFiles.get(link).push(file.replace(process.cwd() + '/', ''));
    }
  }

  const linksToCheck = Array.from(allLinks).filter(link => {
    return !SKIP_DOMAINS.some(domain => link.includes(domain));
  });

  console.log(`📚 Found ${linksToCheck.length} unique external links in ${files.length} files`);

  // Process in batches
  const results = [];
  for (let i = 0; i < linksToCheck.length; i += CONCURRENCY) {
    const batch = linksToCheck.slice(i, i + CONCURRENCY);
    const batchResults = await Promise.all(batch.map(checkLink));
    results.push(...batchResults);

    // Progress
    const checked = Math.min(i + CONCURRENCY, linksToCheck.length);
    process.stdout.write(`\r🔍 Checked ${checked}/${linksToCheck.length}...`);
  }
  console.log('\n');

  const failed = results.filter(r => !r.ok);
  const passed = results.filter(r => r.ok);

  console.log(`✅ ${passed.length} links passed`);
  console.log(`❌ ${failed.length} links failed\n`);

  if (failed.length > 0) {
    console.log('Failed links:');
    for (const fail of failed) {
      const files = linkToFiles.get(fail.url);
      console.log(`  ${fail.url}`);
      console.log(`    status: ${fail.status}${fail.error ? `, error: ${fail.error}` : ''}`);
      console.log(`    in: ${files.slice(0, 3).join(', ')}${files.length > 3 ? '...' : ''}`);
    }
    process.exit(1);
  }

  console.log('🎉 All external links are valid!');
}

main().catch(err => {
  console.error('❌ Link checker failed:', err);
  process.exit(1);
});
