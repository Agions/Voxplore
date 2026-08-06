#!/usr/bin/env node
//
// SceneFab v1.0.0  - gen-ipc.mjs
//
// 自动从 Rust 源码提取 IPC 命令签名 + 公开类型定义,生成 IpcContracts 表与
// 领域类型 interface,前后端类型单一真相源。
//
// 用法:
//   node scripts/gen-ipc.mjs                重新生成 commands 段 + types 段
//   node scripts/gen-ipc.mjs --check        检查 types.gen.ts 与生成内容一致 (CI)
//   node scripts/gen-ipc.mjs --commands     仅重新生成 commands (IpcContracts)
//   node scripts/gen-ipc.mjs --types        仅重新生成 types (pub struct/enum)
//
// 输入:
//   - apps/desktop/src-tauri/src/commands/*.rs   (#[tauri::command] pub fn ...)
//   - apps/desktop/src-tauri/src/commands/*.rs   (pub struct/enum,带 serde derive)
//   - crates/*/src/**/*.rs                       (pub struct/enum,带 serde derive)
//
// 输出: apps/desktop/src/ipc/types.gen.ts
//   - 替换 /* >>> gen-ipc start */ 至 /* <<< gen-ipc end */ (IpcContracts)
//   - 替换 /* >>> gen-ipc-types start */ 至 /* <<< gen-ipc-types end */ (types)
//
// 类型映射:
//   - 原生 primitive -> string / boolean / number
//   - chrono::DateTime<Utc> -> string (ISO 8601)
//   - std::path::PathBuf     -> string (序列化后)
//   - semver::Version        -> string (序列化后)
//   - Vec<T>      -> T[]
//   - Option<T>   -> T | null
//   - HashMap<K,V>-> Record<K, V>
//   - serde_json::Value -> unknown
//
// 字段命名: 读取每个 struct 的 #[serde(rename_all = "X")] 决定 snake/camel/kebab 策略
// 类型命名: TS_ALIASES 用于桥接 Rust/TS 命名差异 (SystemInfo -> AppSystemInfo)
//

import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const COMMANDS_DIR = resolve(HERE, "../src-tauri/src/commands");
const CRATES_DIR = resolve(HERE, "../crates");
const TYPES_FILE = resolve(HERE, "../src/ipc/types.gen.ts");

// ── 类型映射表 ──────────────────────────────────────────────────────
const PRIMITIVE_MAP = {
  String: "string",
  str: "string",
  "&'static str": "string",
  "&str": "string",
  bool: "boolean",
  u8: "number",
  u16: "number",
  u32: "number",
  u64: "number",
  u128: "number",
  i8: "number",
  i16: "number",
  i32: "number",
  i64: "number",
  i128: "number",
  f32: "number",
  f64: "number",
  usize: "number",
  isize: "number",
  SceneCut: "number",
  PathBuf: "string",
  "std::path::PathBuf": "string",
  Version: "string",
  "semver::Version": "string",
  "serde_json::Value": "unknown",
  Value: "unknown",
  "()": "void",
};

// Rust 类型名 → TS 类型名 别名表
const TS_ALIASES = {
  SystemInfo: "AppSystemInfo",
  StepDef: "PipelineStepDef",
  DateTime: "string",
};

// 跳过生成的 internal / edge-case 类型 (与 IPC 无关或 wire 格式有手动 override)
const SKIP_TYPES = new Set([
  "LlmProviderKind", // kebab-case 把 DeepSeek 序列化为 "deep-seek",但手工约定是 "deepseek"
  "AppContext",
  "AppContextBuilder",
  "ServiceContainer", // 服务容器 (runtime-only)
  "Ffmpeg", // helper struct,只用于调用 ffmpeg 二进制
  "LlmRequest",
  "LlmResponse",
  "OpenAiCompatible",
  "LlmManager",
  "ClaudeProvider",
  "GeminiProvider",
  "TtsRequest",
  "TtsOutcome",
  "OpenAiTtsOptions",
  "OpenAiTtsEngine",
  "EdgeTtsOptions",
  "EdgeTtsEngine",
  "GptSovitsOptions",
  "TtsEngineConfig",
  "PipelineDeps",
  "IngestStep",
  "SceneSplitStep",
  "ScriptGenStep",
  "VoiceCaptionsStep",
  "SubtitleStep",
  "ComposeStep",
  "ExportStep",
  "Pipeline",
  "PipelineService",
  "PipelineEvent",
  "UpdateEvent", // broadcast events
  "AssetError",
  "UpdateError", // thiserror::Error
  "LoggingService",
]);

// ── 字符串工具 ──────────────────────────────────────────────────────

function snakeToCamel(name) {
  return name.replace(/_([a-z0-9])/g, (_, ch) => ch.toUpperCase());
}

function pascalToSnake(name) {
  return name.replace(/([A-Z])/g, (m, ch, i) =>
    i === 0 ? ch.toLowerCase() : `_${ch.toLowerCase()}`,
  );
}

function pascalToKebab(name) {
  return name.replace(/([A-Z])/g, (m, ch, i) =>
    i === 0 ? ch.toLowerCase() : `-${ch.toLowerCase()}`,
  );
}

function snakeToPascal(name) {
  return name
    .split("_")
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join("");
}

// 根据 serde rename_all 策略,转换 Rust 字段/变体名 -> wire 名
function renameByStrategy(name, strategy) {
  switch (strategy) {
    case "camelCase":
      return snakeToCamel(name);
    case "snake_case":
      // Rust enum variants 通常为 PascalCase,转为 snake_case
      return pascalToSnake(name);
    case "kebab-case":
      return pascalToKebab(name);
    case "PascalCase":
      return snakeToPascal(name);
    case "SCREAMING_SNAKE_CASE":
      return name.toUpperCase();
    case "lowercase":
      return name.toLowerCase();
    case "UPPERCASE":
      return name.toUpperCase();
    default:
      return name;
  }
}

function findMatchingAngle(content, start) {
  let depth = 1;
  for (let i = start + 1; i < content.length; i++) {
    const ch = content[i];
    if (ch === "<") depth++;
    else if (ch === ">") {
      depth--;
      if (depth === 0) return i + 1;
    }
  }
  return -1;
}

function findMatchingBrace(content, openIdx) {
  let depth = 1;
  for (let i = openIdx + 1; i < content.length; i++) {
    const ch = content[i];
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

// 在 source 中,从 startIdx 向前查找最近的 `#[serde(...)]` 块,返回 rename_all 策略
// 关键: 只扫描到前一个 item 边界 (pub struct / pub enum / pub fn / pub trait),避免继承前一个 item 的 #[serde]
function findRenameAll(source, startIdx) {
  const slice = source.slice(0, startIdx);
  // 找到所有 #[serde(...)] 块及其位置
  const serdeBlocks = [
    ...slice.matchAll(/#\[serde(?::[a-z_]+)?\(([^)]*)\)\]/g),
  ];
  // 找到所有 #[derive(...)] 块 (标记 item 起始)
  const itemStarts = [
    ...slice.matchAll(
      /\b(?:pub\s+)?(?:struct|enum|fn|trait|impl|const|static)\b/g,
    ),
  ];
  // 最近的 item 起始位置
  const lastItemStart =
    itemStarts.length > 0 ? itemStarts[itemStarts.length - 1].index : 0;

  // 只取 >= lastItemStart 的 serde 块
  for (let i = serdeBlocks.length - 1; i >= 0; i--) {
    const idx = serdeBlocks[i].index;
    if (idx < lastItemStart) break;
    const inner = serdeBlocks[i][1];
    const m = /rename_all\s*=\s*"([^"]+)"/.exec(inner);
    if (m) return m[1];
  }
  return null;
}

// ── 类型映射 ────────────────────────────────────────────────────────

const stripPathPrefix = (t) =>
  t
    .replace(/^scenefab_[a-z_]+::/g, "")
    .replace(/^tauri::/g, "")
    .replace(/^std::/g, "")
    .replace(/^chrono::/g, "")
    .replace(/^semver::/g, "");

function mapType(rawType) {
  let t = rawType.trim();

  const vecM = /^Vec<(.+)>$/.exec(t);
  if (vecM) return `${mapType(vecM[1])}[]`;

  const optM = /^Option<(.+)>$/.exec(t);
  if (optM) {
    const inner = mapType(optM[1]);
    return inner === "unknown" ? "unknown" : `${inner} | null`;
  }

  const mapM = /^(?:HashMap|BTreeMap|IndexMap)<(.+),\s*(.+)>$/.exec(t);
  if (mapM) return `Record<${mapType(mapM[1])}, ${mapType(mapM[2])}>`;

  const resM = /^Result<(.+),\s*[^>]+>$/.exec(t);
  if (resM) return mapType(resM[1]);

  if (/^chrono::DateTime/.test(t) || /^DateTime</.test(t)) return "string";

  t = stripPathPrefix(t);

  if (TS_ALIASES[t]) return TS_ALIASES[t];
  if (PRIMITIVE_MAP[t]) return PRIMITIVE_MAP[t];

  return t;
}

// ── commands 段: IPC 函数签名 ──────────────────────────────────────────

// 用单条 regex 一次性匹配整段 `name: State<...>` 并清空。
// 注意: 不要尝试在 replace 回调中用 source.slice 重构字符串 —
// V8 的 String#replace 只会用回调返回值替换"匹配段"本身,
// 外层 slice 会错位拼接成错误结果。
function stripRuntimeParams(rawArgs) {
  return rawArgs
    .replace(/\b\w+\s*:\s*State\s*<[^>]*>\s*,?\s*/g, "")
    .replace(/\b\w+\s*:\s*(?:tauri::)?AppHandle\b\s*,?\s*/g, "")
    .replace(/\b\w+\s*:\s*(?:tauri::)?(?:Window|Webview)\b\s*,?\s*/g, "");
}

function parseParams(rawArgs) {
  // 先用 regex 一次性去除 Tauri runtime 参数 (State<'_, X> / AppHandle / Window / Webview),
  // 不论参数名叫 state/app/window/webview 还是 reg/tr,统一清空。
  // 用单条 regex 一次性匹配整段 `name: State<...>` 并清空。
  const argsClean = rawArgs
    .replace(/\b\w+\s*:\s*State\s*<[^>]*>\s*,?\s*/g, "")
    .replace(/\b\w+\s*:\s*(?:tauri::)?AppHandle\b\s*,?\s*/g, "")
    .replace(/\b\w+\s*:\s*(?:tauri::)?(?:Window|Webview)\b\s*,?\s*/g, "");
  const segments = [];
  let buf = "";
  let angle = 0;
  let paren = 0;
  for (let i = 0; i < argsClean.length; i++) {
    const ch = argsClean[i];
    if (ch === "<") angle++;
    else if (ch === ">") angle--;
    else if (ch === "(") paren++;
    else if (ch === ")") paren--;
    else if (ch === "," && angle === 0 && paren === 0) {
      const trimmed = buf.trim();
      if (trimmed) segments.push(trimmed);
      buf = "";
      continue;
    }
    buf += ch;
  }
  const lastTrimmed = buf.trim();
  if (lastTrimmed) segments.push(lastTrimmed);

  const params = [];
  for (const seg of segments) {
    if (!seg) continue;
    const m = /^(\w+)\s*:\s*(.+)$/.exec(seg);
    if (!m) {
      throw new Error(`无法解析参数: "${seg}"`);
    }
    params.push({ name: snakeToCamel(m[1]), type: mapType(m[2]) });
  }
  return params;
}

function parseReturn(rawRet) {
  let t = rawRet.trim();
  if (t === "" || t === "()" || /^->\s*\(\)\s*$/.test(t)) return "void";
  t = t.replace(/^->\s*/, "").trim();
  const resM =
    /^Result<(.+),\s*(?:String|tauri::Error|anyhow::Error|[^>]+)>$/.exec(t);
  if (resM) return mapType(resM[1].trim());
  return mapType(t);
}

function extractSignatures(source) {
  const cleaned = source.replace(/\/\/[^\n]*/g, "");
  const sigs = [];
  const re =
    /#\[tauri::command\][\s\S]*?pub\s+(?:async\s+)?fn\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^{]+?))?(?:\s+where[^{]*)?\s*\{/g;
  let m;
  while ((m = re.exec(cleaned)) !== null) {
    const name = m[1];
    const argsRaw = m[2];
    const retRaw = m[3] ?? "";
    try {
      const params = parseParams(argsRaw);
      const result = parseReturn(retRaw);
      sigs.push({ name, params, result });
    } catch (err) {
      console.error(`[gen-ipc] 解析失败 (${name}): ${err.message}`);
    }
  }
  return sigs;
}

function renderContracts(sigs) {
  const domainOrder = [
    "app",
    "project",
    "pipeline",
    "settings",
    "update",
    "assets",
    "export",
    "help",
    "voice",
    "script",
    "detect",
    "subtitle",
    "video",
    "i18n",
    "window",
    "diagnostics",
    "llm",
    "plugin",
  ];
  const grouped = new Map();
  for (const sig of sigs) {
    const prefix = sig.name.split("_")[0];
    if (!grouped.has(prefix)) grouped.set(prefix, []);
    grouped.get(prefix).push(sig);
  }
  for (const list of grouped.values())
    list.sort((a, b) => a.name.localeCompare(b.name));

  const lines = [];
  lines.push(
    "export interface IpcContracts {",
    "  greet: {",
    "    args: { name: string };",
    "    result: string;",
    "  };",
  );
  for (const domain of domainOrder) {
    const list = grouped.get(domain) ?? [];
    if (list.length === 0) continue;
    const bar = "─".repeat(7);
    lines.push(`  // ${bar} ${domain} · ${list.length} 个 ${bar}`);
    for (const sig of list) {
      lines.push(`  ${sig.name}: {`);
      if (sig.params.length === 0) {
        lines.push("    args: void;");
      } else {
        const fields = sig.params
          .map((p) => `      ${p.name}: ${p.type};`)
          .join("\n");
        lines.push("    args: {");
        lines.push(fields);
        lines.push("    };");
      }
      lines.push(`    result: ${sig.result};`);
      lines.push("  };");
    }
  }
  lines.push("}");
  return lines.join("\n");
}

// ── types 段: pub struct/enum 定义 ──────────────────────────────────────

function parseStructBody(body) {
  const segments = [];
  let buf = "";
  let angle = 0;
  let paren = 0;
  let brace = 0;
  for (let i = 0; i < body.length; i++) {
    const ch = body[i];
    if (ch === "<") angle++;
    else if (ch === ">") angle--;
    else if (ch === "(") paren++;
    else if (ch === ")") paren--;
    else if (ch === "{") brace++;
    else if (ch === "}") brace--;
    else if (ch === "," && angle === 0 && paren === 0 && brace === 0) {
      const trimmed = buf.trim();
      if (trimmed) segments.push(trimmed);
      buf = "";
      continue;
    }
    buf += ch;
  }
  const last = buf.trim();
  if (last) segments.push(last);

  const fields = [];
  for (const seg of segments) {
    const m = /^pub\s+(\w+)\s*:\s*(.+)$/.exec(seg);
    if (!m) continue;
    fields.push({
      rustName: m[1],
      type: mapType(m[2].trim()),
    });
  }
  return fields;
}

function parseEnumBody(body) {
  const segments = [];
  let buf = "";
  let angle = 0;
  let paren = 0;
  let brace = 0;
  for (let i = 0; i < body.length; i++) {
    const ch = body[i];
    if (ch === "<") angle++;
    else if (ch === ">") angle--;
    else if (ch === "(") paren++;
    else if (ch === ")") paren--;
    else if (ch === "{") brace++;
    else if (ch === "}") brace--;
    else if (ch === "," && angle === 0 && paren === 0 && brace === 0) {
      const trimmed = buf.trim();
      if (trimmed) segments.push(trimmed);
      buf = "";
      continue;
    }
    buf += ch;
  }
  const last = buf.trim();
  if (last) segments.push(last);

  const variants = [];
  for (const seg of segments) {
    if (/^#\[/.test(seg)) continue;
    const m = /^(\w+)/.exec(seg);
    if (!m) continue;
    variants.push(m[1]);
  }
  return variants;
}

function extractStructDefinitions(source) {
  const cleaned = source.replace(/\/\/[^\n]*/g, "");
  const items = [];

  const structRe = /\bpub\s+struct\s+(\w+)(?:<[^>]+>)?\s*\{/g;
  let m;
  while ((m = structRe.exec(cleaned)) !== null) {
    const rustName = m[1];
    if (SKIP_TYPES.has(rustName)) continue;
    const structStartIdx = m.index;
    const openIdx = m.index + m[0].length - 1;
    const closeIdx = findMatchingBrace(cleaned, openIdx);
    if (closeIdx < 0) continue;
    const body = cleaned.slice(openIdx + 1, closeIdx);
    const fields = parseStructBody(body);
    if (fields.length === 0) continue;
    const renameAll = findRenameAll(cleaned, structStartIdx);
    // 应用字段名转换
    const converted = fields.map((f) => ({
      name: renameByStrategy(f.rustName, renameAll),
      type: f.type,
    }));
    items.push({
      kind: "struct",
      rustName,
      tsName: TS_ALIASES[rustName] ?? rustName,
      fields: converted,
      renameAll,
    });
  }

  const enumRe = /\bpub\s+enum\s+(\w+)(?:<[^>]+>)?\s*\{/g;
  while ((m = enumRe.exec(cleaned)) !== null) {
    const rustName = m[1];
    if (SKIP_TYPES.has(rustName)) continue;
    const enumStartIdx = m.index;
    const openIdx = m.index + m[0].length - 1;
    const closeIdx = findMatchingBrace(cleaned, openIdx);
    if (closeIdx < 0) continue;
    const body = cleaned.slice(openIdx + 1, closeIdx);
    const variants = parseEnumBody(body);
    if (variants.length === 0) continue;
    const renameAll = findRenameAll(cleaned, enumStartIdx);
    const converted = variants.map((v) => renameByStrategy(v, renameAll));
    items.push({
      kind: "enum",
      rustName,
      tsName: TS_ALIASES[rustName] ?? rustName,
      variants: converted,
      renameAll,
    });
  }

  return items;
}

function dedupeByTsName(items) {
  const seen = new Set();
  const out = [];
  for (const it of items) {
    if (seen.has(it.tsName)) continue;
    seen.add(it.tsName);
    out.push(it);
  }
  return out;
}

function renderTypes(items) {
  if (items.length === 0) return "";
  const lines = [];
  for (const it of items) {
    if (it.kind === "struct") {
      const fields = it.fields.map((f) => `  ${f.name}: ${f.type};`).join("\n");
      lines.push(
        `// Rust 端 ${it.rustName} (pub struct${it.renameAll ? `, rename_all = "${it.renameAll}"` : ""})`,
        `export interface ${it.tsName} {`,
        fields,
        "}",
        "",
      );
    } else if (it.kind === "enum") {
      const variants = it.variants.map((v) => `  | "${v}"`).join("\n");
      lines.push(
        `// Rust 端 ${it.rustName} (pub enum${it.renameAll ? `, rename_all = "${it.renameAll}"` : ""})`,
        `export type ${it.tsName} =\n${variants};`,
        "",
      );
    }
  }
  return lines.join("\n").replace(/\n+$/, "\n");
}

// ── marker patcher ─────────────────────────────────────────────────

function patchMarker(content, startTag, endTag, block) {
  const startIdx = content.indexOf(startTag);
  const endIdx = content.indexOf(endTag);
  if (startIdx === -1 || endIdx === -1) {
    throw new Error(
      `types.gen.ts 缺少 ${startTag} / ${endTag} 标记。请先用 SearchReplace 加入。`,
    );
  }
  const before = content.slice(0, startIdx + startTag.length);
  const after = content.slice(endIdx);
  return before + "\n" + block + "\n" + after;
}

// ── 文件发现 ────────────────────────────────────────────────────────

function listCommandFiles() {
  if (!statSync(COMMANDS_DIR, { throwIfNoEntry: false })?.isDirectory()) {
    console.error(`[gen-ipc] 找不到 commands 目录: ${COMMANDS_DIR}`);
    process.exit(1);
  }
  return readdirSync(COMMANDS_DIR)
    .filter((f) => f.endsWith(".rs") && f !== "mod.rs")
    .sort()
    .map((f) => join(COMMANDS_DIR, f));
}

function listCrateFiles() {
  if (!statSync(CRATES_DIR, { throwIfNoEntry: false })?.isDirectory()) {
    return [];
  }
  const files = [];
  for (const crate of readdirSync(CRATES_DIR)) {
    const srcDir = join(CRATES_DIR, crate, "src");
    if (!statSync(srcDir, { throwIfNoEntry: false })?.isDirectory()) continue;
    walkRsFiles(srcDir, files);
  }
  return files.sort();
}

function walkRsFiles(dir, out) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full, { throwIfNoEntry: false });
    if (!st) continue;
    if (st.isDirectory()) {
      walkRsFiles(full, out);
    } else if (st.isFile() && entry.endsWith(".rs")) {
      out.push(full);
    }
  }
}

// ── 入口 ────────────────────────────────────────────────────────────

function genCommands() {
  const files = listCommandFiles();
  const allSigs = [];
  for (const file of files) {
    const src = readFileSync(file, "utf8");
    const sigs = extractSignatures(src);
    console.log(
      `[gen-ipc][commands] ${file.replace(resolve(HERE, "../..") + "/", "")}: ${sigs.length} 个命令`,
    );
    allSigs.push(...sigs);
  }
  console.log(`[gen-ipc][commands] 共 ${allSigs.length} 个命令`);
  return renderContracts(allSigs);
}

function genTypes() {
  const allItems = [];
  const allFiles = [...listCommandFiles(), ...listCrateFiles()];
  for (const file of allFiles) {
    const src = readFileSync(file, "utf8");
    const items = extractStructDefinitions(src);
    if (items.length === 0) continue;
    const rel = file.replace(resolve(HERE, "../..") + "/", "");
    console.log(
      `[gen-ipc][types] ${rel}: ${items.length} 个类型 (${items
        .map((i) => `${i.kind}:${i.rustName}`)
        .join(", ")})`,
    );
    allItems.push(...items);
  }
  const deduped = dedupeByTsName(allItems);
  console.log(
    `[gen-ipc][types] 共 ${allItems.length} 个原始,去重后 ${deduped.length} 个`,
  );
  return renderTypes(deduped);
}

function main() {
  const args = process.argv.slice(2);
  const checkOnly = args.includes("--check");
  const commandsOnly = args.includes("--commands");
  const typesOnly = args.includes("--types");

  const original = readFileSync(TYPES_FILE, "utf8");
  let patched = original;

  const wantCommands = !typesOnly;
  const wantTypes = !commandsOnly;

  if (wantCommands) {
    const block = genCommands();
    patched = patchMarker(
      patched,
      "/* >>> gen-ipc start */",
      "/* <<< gen-ipc end */",
      block,
    );
  }

  if (wantTypes) {
    const block = genTypes();
    patched = patchMarker(
      patched,
      "/* >>> gen-ipc-types start */",
      "/* <<< gen-ipc-types end */",
      block,
    );
  }

  if (checkOnly) {
    if (patched === original) {
      console.log("[gen-ipc] OK - types.gen.ts 与生成内容一致");
      process.exit(0);
    } else {
      console.error(
        "[gen-ipc] FAIL - types.gen.ts 与生成内容不一致,请运行 pnpm gen:ipc 重新生成",
      );
      console.error(
        "差异位置: 第一个不同的字符索引为 " + firstDiffIndex(original, patched),
      );
      process.exit(1);
    }
  }

  writeFileSync(TYPES_FILE, patched, "utf8");
  console.log(`[gen-ipc] OK - 已更新 ${TYPES_FILE}`);
}

function firstDiffIndex(a, b) {
  const len = Math.min(a.length, b.length);
  for (let i = 0; i < len; i++) if (a[i] !== b[i]) return i;
  return len;
}

main();
