# JARVIS 2.0 Accessibility & Inclusivity Standards (a11y)

## 1. Compliance Level

JARVIS 2.0 is built to adhere to **WCAG 2.1 AA** accessibility standards, ensuring the AI command center is fully operable for users utilizing screen readers, keyboard navigation, or high-contrast assistive tools.

---

## 2. Implemented Accessibility Features

### 2.1 Keyboard Navigation & Focus Trapping
- **`Ctrl+K` / `Cmd+K`**: Opens the Command Palette instantly from any workspace.
- **`Escape`**: Closes open modals, palettes, and drawers, safely returning focus to the triggering element.
- **`Tab` / `Shift+Tab`**: Navigates through interactive controls in logical DOM order. Focus outlines utilize visible cyan rings (`focus:outline-none focus:ring-2 focus:ring-cyan-400`).
- **`Ctrl+Shift+D`**: Toggles developer DSP diagnostics overlay.

### 2.2 Semantic HTML & ARIA Attributes
- **Live Regions (`aria-live="polite"`)**: Used in the message turn container and Toast Notification System to announce dynamic assistant responses and async alerts to screen readers.
- **Screen Reader Labels (`aria-label`, `sr-only`)**: Provided on all icon-only buttons (search, navigation tabs, audio controls, file download triggers).
- **Proper Heading Hierarchy**: Semantic `h1`, `h2`, `h3`, `h4` tags structured across all workspaces.

### 2.3 Color Contrast & Visual Clarity
- High contrast foreground-to-background ratio (minimum 4.5:1 for normal text, 7:1 for enhanced badges).
- No critical information is conveyed by color alone — status icons accompany all online, warning, and error states.

### 2.4 Multimodal Input & Output
- Full parity between **Voice Input (Speech-to-Text)** and **Text Input (Keyboard/Form)**.
- Visual status indicators accompany all voice activity states.
