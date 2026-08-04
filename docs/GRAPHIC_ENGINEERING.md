# Production Graphic Engineering

This document defines the visual-production contract for PersianToolbox Content Factory.

## Problem statement

A technically valid PNG is not necessarily publishable. The previous pipeline validated file existence, checksums, dimensions, and risk metadata but did not validate linguistic quality, typography, composition, visual density, brand hierarchy, or approval integrity.

## Non-negotiable quality gates

A bundle may be marked `READY_FOR_MANUAL_SCHEDULING` only when all gates below pass.

### 1. Copy gate

- Human-readable Persian sentence structure.
- No raw page suffixes such as `- جعبه ابزار فارسی` in generated hooks.
- No duplicated title in hook and body.
- No truncated sentence fragments.
- No internal enum values such as `tool-demo` in audience-visible content.
- Caption, CTA, alt text, and image copy are normalized independently.

### 2. Typography gate

- Offline/local font stack; rendering must not depend on a remote CSS URL.
- `document.fonts.ready` must resolve before screenshot capture.
- RTL direction and Persian shaping must be verified in the browser.
- Minimum effective font sizes:
  - Feed heading: 54 px
  - Feed body: 28 px
  - Story heading: 64 px
  - CTA: 26 px
- No clipped glyphs or malformed ZWNJ.

### 3. Composition gate

Every output must contain:

- Brand mark.
- Persian category label.
- One concise headline.
- One supporting line.
- A meaningful visual motif or product mockup.
- A visible CTA.
- Platform-specific safe margins.

Whitespace is intentional, but an image with more than 88% near-white pixels fails.

### 4. Visual-material gate

At least one of the following must be present:

- Product/page screenshot.
- Purpose-built vector illustration.
- Document cards, workflow diagram, or feature chips.
- Branded device/browser mockup.

Text-only white canvases are forbidden.

### 5. Automated visual QA

The renderer must emit a metrics sidecar per PNG:

- dimensions
- near-white ratio
- foreground bounding box ratio
- edge density
- dominant-color count
- file size
- perceptual hash

Fail conditions:

- wrong dimensions
- near-white ratio > 0.88
- foreground bounding box area < 0.22
- file size < 45 KB for production PNGs
- missing visual-material marker

### 6. Approval integrity

- Export requires a real stored approval.
- `approval_id` must come from the stored approval record; caller-supplied empty values are forbidden.
- Manifest may not declare `READY_FOR_MANUAL_SCHEDULING` with an empty approval ID.
- Any content or render change after approval invalidates the bundle.

### 7. Human proof gate

CI must publish a review artifact containing:

- contact sheet of all three sizes
- caption, CTA, alt text, and hashtags
- visual metrics JSON
- manifest preview

The first production canary after any renderer/design-system change requires explicit human approval of the artifact.

## Design direction

The default PersianToolbox visual language is a structured editorial/product system:

- dark navy typography
- PersianToolbox blue as the primary action color
- warm amber accent
- soft neutral canvas
- layered cards and document metaphors
- strong right-aligned hierarchy
- no gradients that reduce readability
- no generic English taxonomy in final assets

## Release policy

`v1.1.5` canary assets are rejected. The next publishable release must satisfy this document and include a fresh approval and fresh bundle.