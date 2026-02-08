export const UI_STYLES = `
.ui-root {
  color-scheme: light dark;
  background: var(--ui-color-bg);
  color: var(--ui-color-text-primary);
  font-family: var(--ui-font-body);
  font-size: var(--ui-font-size-md);
  line-height: var(--ui-line-height-normal);
  letter-spacing: 0.005em;
  min-height: 100%;
}

.ui-root[data-ui-theme="dark"] {
  color-scheme: dark;
}

.ui-root[data-ui-theme="light"] {
  color-scheme: light;
}

.ui-window {
  background: var(--ui-color-surface);
  border: 1px solid var(--ui-color-border);
  border-radius: var(--ui-radius-md);
  box-shadow: var(--ui-elevation-2);
  padding: var(--ui-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--ui-space-sm);
}

.ui-container,
.ui-inspector-root,
.ui-transcript-root,
.ui-problems-root,
.ui-debugger-root {
  display: flex;
  flex-direction: column;
  gap: var(--ui-space-sm);
}

.ui-widget {
  box-sizing: border-box;
}

.ui-label {
  display: block;
  font-size: var(--ui-font-size-sm);
  font-weight: var(--ui-font-weight-medium);
  color: var(--ui-color-text-secondary);
  text-transform: none;
}

.ui-button,
.ui-list-action-button {
  appearance: none;
  border: 1px solid var(--ui-color-border);
  border-radius: var(--ui-radius-sm);
  background: var(--ui-color-surface-raised);
  color: var(--ui-color-text-primary);
  padding: calc(var(--ui-space-xs) * 0.75) var(--ui-space-sm);
  font-size: var(--ui-font-size-sm);
  font-weight: var(--ui-font-weight-medium);
  transition: background var(--ui-motion-fast) var(--ui-motion-easing),
    border-color var(--ui-motion-fast) var(--ui-motion-easing),
    color var(--ui-motion-fast) var(--ui-motion-easing);
  cursor: pointer;
}

.ui-button:disabled,
.ui-list-action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ui-button:hover,
.ui-list-action-button:hover {
  background: var(--ui-color-surface);
}

.ui-text-input {
  appearance: none;
  border: 1px solid var(--ui-color-border);
  border-radius: var(--ui-radius-sm);
  background: var(--ui-color-surface);
  color: var(--ui-color-text-primary);
  padding: var(--ui-space-xs) var(--ui-space-sm);
  font-size: var(--ui-font-size-sm);
  transition: border-color var(--ui-motion-fast) var(--ui-motion-easing),
    box-shadow var(--ui-motion-fast) var(--ui-motion-easing);
}

.ui-text-input::placeholder {
  color: var(--ui-color-text-muted);
}

.ui-list-shell {
  display: flex;
  flex-direction: column;
  gap: var(--ui-space-xs);
}

.ui-list-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ui-space-xs);
  padding: var(--ui-space-xs);
  background: var(--ui-color-surface-raised);
  border: 1px solid var(--ui-color-border);
  border-radius: var(--ui-radius-sm);
}

.ui-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ui-space-xs);
}

.ui-list-item {
  margin: 0;
}

.ui-list-button {
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  color: inherit;
  padding: var(--ui-space-xs) var(--ui-space-sm);
  border-radius: var(--ui-radius-sm);
  transition: background var(--ui-motion-fast) var(--ui-motion-easing),
    border-color var(--ui-motion-fast) var(--ui-motion-easing);
  cursor: pointer;
}

.ui-list-item.is-selected .ui-list-button {
  background: var(--ui-color-selection);
  border-color: var(--ui-color-selection);
  color: var(--ui-color-selection-text);
}

.ui-list-button:hover {
  background: var(--ui-color-surface-raised);
}

.ui-tree-button {
  appearance: none;
  border: 0;
  background: transparent;
  color: inherit;
  width: 100%;
  text-align: left;
  padding: 0;
  font: inherit;
}

.ui-tree-row {
  padding: var(--ui-space-xs) var(--ui-space-sm);
  border-radius: var(--ui-radius-sm);
}

.ui-tree-row.is-selected {
  background: var(--ui-color-selection);
  color: var(--ui-color-selection-text);
}

.ui-table {
  border: 1px solid var(--ui-color-border);
  border-radius: var(--ui-radius-sm);
  overflow: hidden;
}

.ui-table-header {
  display: flex;
  background: var(--ui-color-surface-raised);
  border-bottom: 1px solid var(--ui-color-border);
}

.ui-table-header-cell,
.ui-table-cell {
  padding: var(--ui-space-xs) var(--ui-space-sm);
  font-size: var(--ui-font-size-sm);
}

.ui-table-row {
  display: flex;
  border-bottom: 1px solid var(--ui-color-border);
}

.ui-table-row:last-child {
  border-bottom: none;
}

.ui-table-row.is-selected {
  background: var(--ui-color-selection);
  color: var(--ui-color-selection-text);
}

.ui-canvas-view,
.ui-webgl-view {
  border-radius: var(--ui-radius-sm);
  background: var(--ui-color-surface-sunken);
  border: 1px solid var(--ui-color-border);
}

.ui-widget :focus-visible {
  outline: 2px solid var(--ui-color-focus);
  outline-offset: 2px;
}

[data-motion="reduced"] * {
  transition: none !important;
  animation: none !important;
}
`;

export const UI_STYLE_ID = "web-ui-styles";
