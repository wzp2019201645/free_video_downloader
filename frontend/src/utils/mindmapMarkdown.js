/** Convert mind-map tree JSON to Markdown for markmap. */

function escapeLabel(label) {
  return String(label || '未命名')
    .replace(/\r?\n/g, ' ')
    .replace(/^\s*#+\s*/, '')
    .trim() || '未命名'
}

export function mindMapTreeToMarkdown(root) {
  if (!root) return '# 思维导图'
  const lines = [`# ${escapeLabel(root.label)}`]

  function walk(node, depth) {
    const indent = '  '.repeat(depth)
    for (const child of node.children || []) {
      lines.push(`${indent}- ${escapeLabel(child.label)}`)
      walk(child, depth + 1)
    }
  }

  walk(root, 0)
  return lines.join('\n')
}
