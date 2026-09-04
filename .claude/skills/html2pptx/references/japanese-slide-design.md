# Japanese Slide Design Reference

Use this reference when generating slides for Japanese audiences or when the user's request is in Japanese. These rules override generic defaults with Japan-specific typography, structure, and information design guidelines.

## Core Principles

1. **Conclusion first** — show the answer/proposal before the reasoning
2. **1 slide = 1 message** — if there are multiple claims, split into separate slides
3. **Density is contextual** — presentation mode (projecting) vs. handout mode (reading) have different text limits
4. **Alignment and grid** — Japanese audiences expect consistent alignment and visual hierarchy
5. **Restraint in color** — 3 colors max (base + main + accent), avoid raw/saturated primary colors

## Character Count Limits

| Element | Max characters | Notes |
|---------|---------------|-------|
| Slide title | 9-13 | Instant perception limit. Noun ending (体言止め) |
| Slide message (assertion) | 50 | One sentence, written as a complete claim |
| Single bullet / line | 40 | ~10 seconds to comprehend |
| Total per slide (presentation mode) | 105 | Target for projected slides |
| Total per slide (handout mode) | 200-285 | Use cards/boxes to organize density |
| Line length (projection) | 20-30 chars | For text read at a glance |
| Line length (reading) | 35-40 chars | For explanatory text |

## Slide Anatomy

Each slide has 3 distinct text layers:

1. **Title** (top) — short, objective, noun-ending. Labels the content, no claims. Example: "売上推移" not "売上が減少"
2. **Message** (below title) — one sentence, max 50 chars, contains the assertion with a comparison target and quantified difference. Example: "前年比15%増、目標を3ヶ月前倒しで達成"
3. **Body** — bullets, diagrams, or data supporting the message

## Deck Structure (Conclusion-First)

```
表紙 → サマリー → アジェンダ(3-5項目) → 背景 → 課題 → 提案(結論) → 根拠 → 実行計画 → リスク → 結論・次アクション → 付録
```

| Section | Recommended visual |
|---------|-------------------|
| Background/Context | Bullet points |
| Problem/Issue | Graphs (quantitative evidence) |
| Solution/Proposal | Diagrams (flow, process, structure) |
| Effect/Benefit | Diagrams + graphs combined |

## Typography

### Font Stack

```css
font-family: "Noto Sans JP", "BIZ UDPGothic", "Hiragino Kaku Gothic ProN", sans-serif;
```

- **Noto Sans JP** — primary (open source, cross-platform)
- **BIZ UDPGothic** — fallback (universal-design font, high readability)
- Gothic (sans-serif) for all business slides. Mincho (serif) only for formal/literary contexts
- When mixing Japanese and Latin, declare Latin font first: `"Inter", "Noto Sans JP", sans-serif`

### Font Sizes (1600x900px slides)

| Role | Size | Weight | line-height |
|------|------|--------|-------------|
| Slide title | 48-64px | 700 | 1.2-1.3 |
| Section heading | 36-44px | 700 | 1.3 |
| Body text | 24-30px | 400 | 1.6-1.7 |
| Caption / footnote | 16-18px | 400 | 1.4 |
| Data callout (big number) | 56-80px | 700 | 1.1 |
| Unit label (next to number) | 24-28px | 700 | - |

**Rules:**
- Maximum 3 font sizes per slide
- Japanese body text needs `line-height: 1.6` minimum (1.7 recommended). English-designed layouts with 1.4 will feel cramped
- `letter-spacing: 0.05em` for body, `0.02em` for headings
- Numbers should be large, units one size smaller: `<span style="font-size:56px">+15</span><span style="font-size:26px">%</span>`
- Never go below 16px on any slide element

### Japanese Typesetting CSS

```css
.slide {
  line-break: strict;          /* kinsoku shori (禁則処理) */
  word-break: normal;          /* never use break-all for Japanese */
  overflow-wrap: break-word;   /* fallback for long strings */
  font-feature-settings: "palt" 1; /* tighter punctuation spacing */
}
```

### Kinsoku — Prohibited Line Breaks

Characters that must NOT start a line:
```
）〕］｝〉》」』】、。，．？！ー・ぁぃぅぇぉっゃゅょァィゥェォッャュョ
```

Characters that must NOT end a line:
```
（〔［｛〈《「『【
```

### Punctuation Rules

- Use **full-width** punctuation in Japanese text (、。「」) — half-width causes baseline misalignment
- Exception: `?` and `!` may use half-width for visual tension
- Replace parentheses with `|` vertical bars or `[]` brackets where possible for cleaner appearance

## Color

### Palette Rule

3 colors maximum: **base + main + accent**

- Avoid pure/raw colors (原色) — use slightly gray-toned versions
- Avoid pure black (`#000000`) — use dark navy or charcoal (`#1a1a1a`, `#15286d`, `#1e293b`)
- Accent color only for critical emphasis points

### Contrast (WCAG AA + DADS)

| Element | Minimum ratio |
|---------|--------------|
| All text (any size) | 4.5:1 |
| Non-text UI elements (icons, borders) | 3:1 |
| Brand colors used as text | 4.5:1 (adjust brightness if needed) |

Note: Japan Digital Agency (DADS) removes the large-text exemption. Even 48px+ headings must meet 4.5:1.

### Do NOT rely on color alone

- Comparison/status must use labels + shape + icon, not just color
- Charts with thin lines: add text annotations near data points
- If brand color fails contrast, adjust brightness while keeping hue

## Layout

### Safe Margins

For 1600x900px slides: **64-80px horizontal, 48-64px vertical** (approximately 5% of dimensions)

### Alignment

- Left-align Japanese body text — never full-justify on slides (causes ugly gaps)
- Use Z-pattern (left-to-right, top-to-bottom) as default reading flow
- All elements must align to a consistent grid across slides

### Grid System

12-column grid with ~24px gutters works well for 1600x900:

```css
.grid { display: grid; grid-template-columns: repeat(12, 1fr); column-gap: 24px; }
.col4 { grid-column: span 4; }
.col6 { grid-column: span 6; }
.col8 { grid-column: span 8; }
```

### Controlling Line Length

Use `max-width` to prevent lines from running too long:

```css
.body { max-width: 1100px; }  /* ~30-35 chars at 30px */
.reading { max-width: 1300px; } /* ~38-40 chars at 30px */
```

## Icons and Images

- Icons are **supplementary** — meaning must be conveyed by text, not icon alone
- One icon = one concept (do not pack multiple ideas into one icon)
- Use a single icon family consistently (do not mix outline and filled styles)
- Prefer rounded, simple shapes for approachable feel
- Minimum icon size: 20px for slides

## Japanese Base CSS Template

```css
.slide {
  width: 1600px;
  height: 900px;
  margin: 0; padding: 0;
  box-sizing: border-box;
  overflow: hidden;
  position: relative;
  background: #ffffff;
  color: #1a1a1a;
  font-family: "Noto Sans JP", "BIZ UDPGothic", "Hiragino Kaku Gothic ProN", sans-serif;
  line-break: strict;
  word-break: normal;
  font-feature-settings: "palt" 1;
}
.slide-inner {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  padding: 64px 80px;
  box-sizing: border-box;
}
.title {
  font-size: 56px;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.message {
  margin-top: 16px;
  font-size: 28px;
  font-weight: 500;
  line-height: 1.5;
  max-width: 1200px;
}
.h2 {
  font-size: 40px;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: 0.02em;
}
.body {
  font-size: 28px;
  line-height: 1.7;
  letter-spacing: 0.05em;
  max-width: 1100px;
}
.note {
  font-size: 18px;
  line-height: 1.5;
  color: #595959;
}
.num {
  font-size: 56px;
  font-weight: 700;
  line-height: 1.1;
}
.unit {
  font-size: 26px;
  font-weight: 700;
  margin-left: 4px;
}
.cards {
  display: flex;
  gap: 20px;
}
.card {
  flex: 1;
  min-width: 0;
  background: #f5f5f5;
  border-radius: 16px;
  padding: 24px;
  box-sizing: border-box;
}
```

## Pre-Export Checklist (Japanese-Specific)

**Text quality:**
- [ ] Each slide has exactly 1 message
- [ ] Titles use noun endings (体言止め), messages are sentences
- [ ] No slide exceeds 105 chars (presentation mode) or 285 chars (handout mode)
- [ ] No bullet line exceeds 40 chars
- [ ] No unnatural line breaks (kinsoku violations)
- [ ] Punctuation is full-width (、。「」)

**Typography:**
- [ ] Body text line-height is 1.6+
- [ ] Font sizes follow 3-tier hierarchy
- [ ] Numbers are large, units are smaller
- [ ] All text has white-space:nowrap where appropriate
- [ ] Text containers have explicit width/min-width in px

**Visual:**
- [ ] Color palette is 3 colors or fewer
- [ ] All text contrast is 4.5:1+
- [ ] No meaning conveyed by color alone
- [ ] Consistent alignment across all slides
- [ ] Safe margins maintained (64-80px)
