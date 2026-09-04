# Rewrite Patterns

Use this reference when converting web markup into slide-safe HTML/CSS.

## Pattern 1: Page to Slide

Problem:

- full webpage
- header, sidebar, footer, scroll regions
- no single export root

Rewrite:

- create one `.slide` root
- move only presentation content into the slide
- remove navigation and utility chrome
- give the slide explicit width and height

## Pattern 2: Runtime Chart to Static Graphic

Problem:

- chart library renders to `canvas`
- chart appears only after runtime boot

Rewrite:

- replace with inline `svg` when possible
- otherwise replace with pre-rendered image
- if the chart is simple, rebuild it using normal DOM bars or a semantic `table`

Prefer SVG over canvas when editability matters.

## Pattern 3: Responsive Layout to Fixed Layout

Problem:

- layout depends on viewport width
- breakpoints change content flow

Rewrite:

- choose one explicit slide size
- pin widths, heights, padding, and gaps for that size
- author for the slide, not for arbitrary screens

## Pattern 4: Decorative Web Effects to Export-Safe Effects

Problem:

- heavy blur stacks
- blend modes
- masking
- layered clipping

Rewrite:

- replace with standard `linear-gradient(...)`
- replace blend effects with explicit color values
- replace masked shapes with simple rounded blocks or inline SVG
- keep decorative effects visually similar but structurally simpler

## Pattern 5: App UI to Presentation Card

Problem:

- tabs, filters, dropdowns, buttons, badges, and control chrome dominate the markup

Rewrite:

- keep the information-bearing state only
- turn controls into static labels when they explain context
- remove affordances that imply interaction
- present the resulting state as cards, tables, summaries, or diagrams

## Pattern 6: Unsafe Input to Safe Input

Problem:

- scripts
- event handlers
- `javascript:` URLs

Rewrite:

- remove executable code entirely
- keep only presentational markup and safe asset URLs
- ensure the exported preview document can render deterministically without running app logic

## Pattern 8: Pixel-Perfect Slide Fit

Problem:

- slide background does not fill the full PowerPoint canvas
- unwanted white margins or gaps appear around the slide edges
- padding on `.slide` pushes the background inward, leaving blank areas

Rewrite:

- set `margin: 0; padding: 0; box-sizing: border-box; overflow: hidden` on every `.slide`
- apply backgrounds (color, gradient, image) directly on the `.slide` element
- use an inner `div` with `position: absolute; top: 0; left: 0; width: 100%; height: 100%` for content padding
- never put content padding directly on the `.slide` when it has a background
- set `position: relative` on `.slide` so absolute children are scoped correctly
- use only fixed `px` units — never `%`, `vw`, `vh`, `em`, or `rem` for layout dimensions

## Pattern 7: Text Centering in Background-Colored Elements

Problem:

- text inside buttons, badges, or cards with `background-color`/`background` drifts to a wrong position in PPTX
- the PPTX converter maps the background `div` to a shape and the inner `span` to a separate text box — they become independent objects
- flexbox centering on the parent does not propagate into the PPTX text box
- padding-only sizing causes shape and text to misalign

Rewrite:

- do NOT nest `<span>` inside a background `<div>` for buttons — put text directly in the background element
- if nesting is needed, give the inner text element `width: 100%` and `text-align: center`
- always use explicit `width` and `height` on the background element (not padding-only sizing)
- add `text-align: center` and `display: flex; justify-content: center; align-items: center` to the container

This pattern applies to ALL elements where background and text must stay together: buttons, stat cards, badges, tags, CTAs, labels, progress indicators, etc.

## Pattern 9: Styled Tables — `<table>` vs div+flexbox

Problem:

- `<table>` with gradient backgrounds on `<th>` or `<td>` causes text to disappear or shrink to ~6pt in PPTX
- nested `<span>` and `<br/>` inside table cells lose content during conversion
- `border-collapse: separate` and complex cell styling break in native PPTX tables

Root cause: the PPTX converter maps `<table>` to a native PPTX table object, which does not support CSS gradients, and handles inline element nesting poorly.

Rewrite:

- for simple data tables with solid-color backgrounds and plain text, keep `<table>`
- for styled grids with gradient headers, rich cell content (bold titles + bullet lists), or per-cell border-radius, use div+flexbox rows instead
- each "row" is a `display: flex` container; each "cell" is a fixed-width div
- put text directly in the div (Pattern 7 applies) or use `<p>` tags for multi-line content — avoid `<span>` + `<br/>` combos
- apply background colors/gradients on the div, not on table elements

## Pattern 10: Text Wrapping and Splitting Prevention

Problem:

- text in flexbox/grid children wraps unexpectedly in PPTX output
- short text like year numbers ("2022") splits into "202" + "2"
- Japanese headings split mid-word
- headings, labels, stats, or single-line text gets broken across lines
- ALL flex/grid layouts are affected, not just `space-between`

Root cause: the PPTX converter calculates text box width from the HTML layout. Without explicit sizing, auto-sized children may receive far less width than the text needs — even `flex: 1` children can get narrow text boxes.

Rewrite:

- add `white-space: nowrap` on EVERY single-line text element (headings, labels, years, stats, names, badges)
- give ALL flex/grid children an explicit `width` or `min-width` in px — never rely on `flex: 1` alone
- for equal columns, calculate: `(container width - total gaps) / number of columns` and set explicitly
- for large font text (40px+), ensure the container is at least `(char count × font-size × 0.7)` px wide for Latin, `(char count × font-size × 1.1)` px wide for Japanese/CJK
- when in doubt, make the container wider than you think necessary — extra space is invisible, but truncated text is broken

This pattern is the single most common cause of PPTX conversion defects. Apply it to ALL layouts: timelines, grids, stat cards, headers, footers, comparison columns, navigation rows, and any element containing text.

## Template Skeleton

Use this as a default starting point:

```html
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      body {
        margin: 0;
        background: #f3f4f6;
      }

      .slide {
        width: 1600px;
        height: 900px;
        box-sizing: border-box;
        padding: 56px;
        background: #ffffff;
        color: #111827;
        font-family: Inter, Arial, sans-serif;
      }
    </style>
  </head>
  <body>
    <section class="slide">
      <h1>Title</h1>
      <p>Slide-safe content.</p>
    </section>
  </body>
</html>
```

## Rewrite Priorities

Apply fixes in this order:

1. make the export root explicit
2. remove runtime dependencies
3. fix unsupported assets and CORS risks
4. simplify unsupported CSS effects
5. improve editability by replacing raster-prone regions

## Response Pattern

When rewriting for a user, prefer this structure:

- `What changed`
- `Why it is safer for PPTX export`
- `What may still rasterize`
- `Rewritten HTML/CSS`
