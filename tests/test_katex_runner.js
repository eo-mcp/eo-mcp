
const fs = require('fs');
const path = require('path');
const katex = require('C:/Users/sounn/AppData/Local/npm-cache/_npx/8c2cfac42696c54b/node_modules/katex');

let totalTested = 0;
let errors = [];

// 1. Check methodology.html
const htmlContent = fs.readFileSync('methodology.html', 'utf8');

// Match .formula-math-display contents
const formulaMathDisplayRegex = /<div class="formula-math-display">\s*([\s\S]*?)\s*<\/div>/g;
let match;
let displayIndex = 0;
while ((match = formulaMathDisplayRegex.exec(htmlContent)) !== null) {
  displayIndex++;
  let raw = match[1].trim();
  let hasDelim = raw.startsWith('$$') && raw.endsWith('$$');
  let clean = raw;
  if (hasDelim) {
    clean = raw.slice(2, -2).trim();
  }
  totalTested++;
  try {
    katex.renderToString(clean, { throwOnError: true, displayMode: true });
  } catch (err) {
    errors.push({ source: 'methodology.html (.formula-math-display #' + displayIndex + ')', raw: clean.slice(0, 50), error: err.message });
  }
}

// Match all $$ in methodology.html
const ddRegex = /\$\$([\s\S]*?)\$\$/g;
let ddCount = 0;
while ((match = ddRegex.exec(htmlContent)) !== null) {
  ddCount++;
  totalTested++;
  let raw = match[1].trim();
  try {
    katex.renderToString(raw, { throwOnError: true, displayMode: true });
  } catch (err) {
    errors.push({ source: 'methodology.html ($$ #' + ddCount + ')', raw: raw.slice(0, 50), error: err.message });
  }
}

// 2. Check all docs/methodology/*.md files
const mdDir = path.join('docs', 'methodology');
const mdFiles = fs.readdirSync(mdDir).filter(f => f.endsWith('.md'));

for (const f of mdFiles) {
  const content = fs.readFileSync(path.join(mdDir, f), 'utf8');
  let mdMatch;
  let mdDdRegex = /\$\$([\s\S]*?)\$\$/g;
  let fileDd = 0;
  while ((mdMatch = mdDdRegex.exec(content)) !== null) {
    fileDd++;
    totalTested++;
    let raw = mdMatch[1].trim();
    try {
      katex.renderToString(raw, { throwOnError: true, displayMode: true });
    } catch (err) {
      errors.push({ source: f + ' ($$ #' + fileDd + ')', raw: raw.slice(0, 50), error: err.message });
    }
  }

  // Check inline math in markdown
  let cleanMd = content.replace(/```[\s\S]*?```/g, '').replace(/`[^`]+`/g, '').replace(/\$\$[\s\S]*?\$\$/g, '');
  let inlineRegex = /(?<!\$)\$([^\$\n]+)\$(?!\$)/g;
  let fileInline = 0;
  while ((mdMatch = inlineRegex.exec(cleanMd)) !== null) {
    fileInline++;
    totalTested++;
    let raw = mdMatch[1].trim();
    try {
      katex.renderToString(raw, { throwOnError: true, displayMode: false });
    } catch (err) {
      errors.push({ source: f + ' (inline #' + fileInline + ')', raw: raw.slice(0, 50), error: err.message });
    }
  }
}

console.log('Total math expressions tested with KaTeX:', totalTested);
console.log('Total KaTeX parse errors:', errors.length);
if (errors.length > 0) {
  console.log('Errors:');
  errors.forEach(e => console.log(' - ' + e.source + ' -> ' + e.error + ' | RAW: ' + e.raw));
}
