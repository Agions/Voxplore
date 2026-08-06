#!/usr/bin/env node
// Dead/internal-link validator for docs/.
// Scans all .md files under docs/, extracts internal links, verifies targets exist.
// Excludes external http(s) links, mailto:, tel:, anchors, dist/, node_modules/, .vitepress/
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { dirname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');
const DOCS_DIR = join(ROOT, 'docs');

/** 收集 docs/ 下所有 .md 文件 */
function collectMarkdownFiles(dir, acc = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry === 'dist' || entry === '.vitepress') continue;
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      collectMarkdownFiles(full, acc);
    } else if (entry.endsWith('.md')) {
      acc.push(full);
    }
  }
  return acc;
}

/** 从 markdown 提取所有链接 */
function extractLinks(content) {
  const links = [];
  const re = /\[([^\]]+)\]\(([^)]+)\)/g;
  let match;
  while ((match = re.exec(content)) !== null) {
    links.push({ text: match[1], href: match[2] });
  }
  return links;
}

/** 判断是否为内部链接 */
function isInternalLink(href) {
  if (href.startsWith('http://') || href.startsWith('https://')) return false;
  if (href.startsWith('mailto:') || href.startsWith('tel:')) return false;
  if (href.startsWith('#')) return false;
  return true;
}

/** 解析内部链接到目标文件路径 */
function resolveLink(href, currentFile) {
  // 去掉锚点
  const [path] = href.split('#');

  let resolved;
  if (path.startsWith('/')) {
    // 绝对路径：基于 docs/
    resolved = join(DOCS_DIR, path);
  } else {
    // 相对路径：基于当前文件目录
    resolved = resolve(dirname(currentFile), path);
  }

  // VitePress cleanUrls: /foo/bar → /foo/bar.md
  // scene-fab 使用 cleanUrls: false，所以主要检查 .md 文件
  const candidates = [
    resolved,
    `${resolved}.md`,
    join(resolved, 'index.md'),
    ...(path.startsWith('/') ? [join(DOCS_DIR, 'public', path)] : []),
  ];

  for (const c of candidates) {
    if (existsSync(c)) {
      return c;
    }
  }
  return null;
}

/** 主检查 */
function main() {
  const files = collectMarkdownFiles(DOCS_DIR);
  console.log(`📚 Scanning ${files.length} markdown files in docs/...`);

  const errors = [];
  let totalLinks = 0;
  let internalLinks = 0;

  for (const file of files) {
    const content = readFileSync(file, 'utf-8');
    const links = extractLinks(content);
    totalLinks += links.length;

    for (const link of links) {
      if (!isInternalLink(link.href)) continue;
      internalLinks++;

      const target = resolveLink(link.href, file);
      if (!target) {
        const relFile = file.replace(ROOT + sep, '');
        errors.push({
          file: relFile,
          href: link.href,
          text: link.text,
        });
      }
    }
  }

  console.log(`✅ Scanned ${totalLinks} total links (${internalLinks} internal)`);

  if (errors.length === 0) {
    console.log('🎉 No dead links found!');
    process.exit(0);
  }

  console.error(`\n❌ Found ${errors.length} dead link(s):\n`);
  for (const err of errors) {
    console.error(`  ${err.file}`);
    console.error(`    [${err.text}](${err.href})`);
    console.error('');
  }
  process.exit(1);
}

main();
