<template>
  <div v-if="depth === 0" class="mindmap-root">
    <div class="mindmap-node__label mindmap-node__label--root">{{ node.label }}</div>
    <ul v-if="node.children?.length" class="mindmap-children">
      <MindMapTree
        v-for="(child, index) in node.children"
        :key="`${child.label}-${index}`"
        :node="child"
        :depth="1"
      />
    </ul>
  </div>
  <li v-else class="mindmap-item">
    <div
      class="mindmap-node__label"
      :class="`mindmap-node__label--d${Math.min(depth, 3)}`"
    >
      {{ node.label }}
    </div>
    <ul v-if="node.children?.length" class="mindmap-children">
      <MindMapTree
        v-for="(child, index) in node.children"
        :key="`${child.label}-${index}`"
        :node="child"
        :depth="depth + 1"
      />
    </ul>
  </li>
</template>

<script setup>
import MindMapTree from './MindMapTree.vue'

defineOptions({ name: 'MindMapTree' })

defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
})
</script>

<style scoped>
.mindmap-root {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.mindmap-children {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  justify-content: center;
}

.mindmap-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.mindmap-node__label {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8125rem;
  line-height: 1.4;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #374151;
  max-width: 16rem;
  text-align: center;
}

.mindmap-node__label--root {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-color: transparent;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
  max-width: 20rem;
}

.mindmap-node__label--d1 {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #4338ca;
  font-weight: 600;
}

.mindmap-node__label--d2 {
  background: #f5f3ff;
  border-color: #ddd6fe;
  color: #6d28d9;
}

.mindmap-node__label--d3 {
  background: #faf5ff;
  border-color: #e9d5ff;
  color: #7c3aed;
}
</style>
