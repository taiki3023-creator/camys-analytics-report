# Input Contract

Use this reference when deciding whether HTML/CSS is suitable for HTML-to-PPTX export.

## Core Rule

Accept slide-oriented HTML, not arbitrary webpages.

The ideal input is:

- fixed-size
- static at capture time
- self-contained
- visually complete without runtime application logic

## Accept

- One or more `.slide` roots
- Explicit slide dimensions
- Normal DOM text content
- `div`, `section`, `article`, `header`, `footer`
- `h1`-`h6`, `p`, `span`
- `ul`, `ol`, `li`
- `table`, `tr`, `th`, `td`
- `img`
- `svg`
- Basic forms of `input[type="text"]` and `textarea` when treated as simple text

## Accept with Possible Degradation

- `canvas`
- backdrop blur
- icon fonts and icon-only elements
- complex rounded clipping
- some generated gradient and border effects
- SVG that is accepted but may be sanitized and rasterized before export on public surfaces

These can export successfully while losing editability.

## Reject or Rewrite First

- `<script>` tags
- inline event handlers such as `onclick`
- `javascript:` URLs
- `iframe`
- `video`
- `audio`
- `embed`
- `object`
- app shells with navigation, tabs, drawers, filters, and runtime controls
- content that requires hydration, async data loading, or external bootstrapping
- long responsive pages intended for scrolling

## CSS That Usually Works

- `background-color`
- `background-image: linear-gradient(...)`
- `color`
- `opacity`
- `border-*`
- `border-radius`
- `box-shadow`
- `filter: blur()`
- `transform: rotate()`
- `position`
- `width`, `height`
- `padding`, `margin`
- `text-align`
- `font-family`, `font-size`, `font-weight`, `font-style`, `line-height`
- final layouts produced by Flexbox or Grid

## Slide Fit Best Practice

Every `.slide` must have `margin: 0; padding: 0; box-sizing: border-box; overflow: hidden; position: relative`. Backgrounds must be applied on the `.slide` itself, not on an inner wrapper. Content padding goes on an inner layout `div`, not on `.slide`. This ensures the slide fills the PowerPoint canvas edge-to-edge with no white gaps.

## Text Alignment Best Practice

Text inside background-colored elements (buttons, badges, cards) MUST NOT be a separate child element when possible. The PPTX converter splits background shapes and text boxes into independent objects, causing misalignment. Preferred approach: put text directly in the background element with explicit `width`, `height`, `text-align: center`, and flexbox centering. If a child element is necessary, give it `width: 100%` and `text-align: center`. Never rely on padding alone to size background elements — always use explicit dimensions.

## CSS That Commonly Causes Trouble

- `transform: scale()`
- `mix-blend-mode`
- `mask`
- `clip-path` chains
- `background-clip: text`
- filter stacks beyond simple blur
- viewport-driven responsive behavior without fixed slide dimensions

## Asset Constraints

Assume that fonts and images must be readable by the browser at export time.

Watch for:

- images without reliable CORS
- font files without reliable CORS
- tainted `canvas` output caused by cross-origin drawing

## Verdict Heuristic

Use this shorthand:

- `safe`: fixed-size, static, CORS-safe, mostly standard DOM/CSS
- `safe with degradation`: export likely succeeds but some regions rasterize
- `needs rewrite`: structure is web-like or effect-heavy, but content is salvageable
- `out of scope`: input behaves like an application or unsupported document
