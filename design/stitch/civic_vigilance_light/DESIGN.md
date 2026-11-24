---
name: Civic Vigilance Light
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434655'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#747686'
  outline-variant: '#c4c5d7'
  surface-tint: '#2151da'
  primary: '#0037b0'
  on-primary: '#ffffff'
  primary-container: '#1d4ed8'
  on-primary-container: '#cad3ff'
  inverse-primary: '#b7c4ff'
  secondary: '#984800'
  on-secondary: '#ffffff'
  secondary-container: '#ff9245'
  on-secondary-container: '#6b3100'
  tertiary: '#802500'
  on-tertiary: '#ffffff'
  tertiary-container: '#a83300'
  on-tertiary-container: '#ffc9b8'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b7c4ff'
  on-primary-fixed: '#001551'
  on-primary-fixed-variant: '#0039b5'
  secondary-fixed: '#ffdbc8'
  secondary-fixed-dim: '#ffb689'
  on-secondary-fixed: '#311300'
  on-secondary-fixed-variant: '#743500'
  tertiary-fixed: '#ffdbd0'
  tertiary-fixed-dim: '#ffb59d'
  on-tertiary-fixed: '#390c00'
  on-tertiary-fixed-variant: '#832600'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 44px
    fontWeight: '800'
    lineHeight: 52px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.005em
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-mono-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: -0.01em
  label-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-ui:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-2xs: 0.25rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
  space-3xl: 4rem
---

## Brand & Style

This design system serves a mission-critical dual audience: citizens seeking validation before conducting digital transactions, and law enforcement analysts executing real-time threat triaging for Rajasthan Police. The emotional core is defined by authority without intimidation, sovereign reliability, and absolute clarity. The citizen experience must feel protective, swift, and unambiguous; the investigator console must feel forensic, high-density, and uncompromisingly precise.

The aesthetic philosophy draws on **State Modernism with Regional Warmth**:
- **Pristine Precision**: Strictly light mode throughout. No dark mode fallbacks or night-shift inversions. Crisp white foregrounds sit atop subtle off-white and sandstone ground planes.
- **Civic Trust & Saffron Heritage**: The authoritative weight of Rajasthan Police institutional blue balanced against the architectural warmth of Jodhpur and Jaisalmer sandstone hues.
- **Glass & Micro-Tactility**: Ultra-subtle translucent card structures with tight, low-contrast ghost borders (`rgba(15, 23, 42, 0.06)`) and ultra-diffuse ambient depth, completely avoiding murky dropped shadows or heavy dark cards.
- **Multi-Script Parity**: Fluent handling of Hindi (Devanagari) alongside Latin typographic scales, ensuring typographic optical weight and vertical metrics remain identical across linguistic contexts.

## Colors

The system uses an uncompromising, strictly light color palette designed to maximize daylight readability in patrol vehicles, field units, and civic kiosks, as well as prolonged analytical focus in cyber monitoring rooms.

### Surface Architecture
- **Primary Canvas (`#F7F8FB`)**: Neutral, cool off-white that prevents screen glare and sets visual distance from foreground panels.
- **Section Accent Background (`#FBF7F1`)**: Warm, sandstone-tinted surface utilized for thematic civic banners, regional advisory bands, or public awareness modules.
- **Elevated Canvas (`#FFFFFF`)**: Pure white base for primary operational cards, modals, and forensic tables.
- **Glass Overlay Canvas (`rgba(255, 255, 255, 0.78)`)**: Used for sticky headers, verification docks, and contextual overlay cards, paired with a 16px backdrop blur.

### Threat & Risk Classification
All risk states must enforce a three-layer signal: background tint, foreground text/border, and an accompanying explicit semantic icon (e.g., shield-alert, alert-triangle, check-circle). Color alone is never used to convey danger.
- **Critical / High Threat**: `#DC2626` over `#FEF2F2`. Indicates confirmed cyber-fraud records, active mule accounts, or blocklisted routing endpoints.
- **Suspicious / Medium Threat**: `#D97706` over `#FFFBEB`. Signals flagged entities, recent anomalous volume, or unverified high-velocity transactions.
- **Verified Safe / Low Threat**: `#059669` over `#ECFDF5`. Confirms legitimate state gateways, authenticated police registries, or verified corporate accounts.

### Entity Identifier System
Forensic data tags employ dedicated chromatic tokens to ensure instant cognitive recognition when reviewing dense logs, relationship graphs, and case dossiers:
- **UPI Handles**: `#7C3AED`
- **Phone Numbers**: `#2563EB`
- **Bank Accounts**: `#B45309`
- **IFSC Codes**: `#A16207`
- **Domains**: `#0D9488`
- **URLs / Endpoints**: `#475569`
- **Email Addresses**: `#0891B2`
- **Telegram Channels / Handles**: `#0284C7`
- **IP Addresses**: `#E11D48`
- **Crypto Wallets / Hashes**: `#EA580C`
- **App Package Names**: `#4F46E5`
- **Signing Certificates**: `#6D28D9`

## Typography

Typography balances civic legibility with forensic precision.

### Typeface Stacks
1. **Primary UI & Headings**: `Plus Jakarta Sans`, supplemented by system fallbacks `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`. Used for navigational anchors, citizen instructions, and section titles.
2. **Bilingual Script Support (Hindi)**: `Noto Sans Devanagari`. When rendering Hindi text strings (e.g., "परखो, फिर भरोसो"), apply a font-size scale multiplier of **1.05x** relative to the matching Latin token to balance optical cap-height and vowel conjunct visibility.
3. **Forensic & Data Monospace**: `JetBrains Mono`. Mandated for all identifier values (UPI VPA, Mobile Numbers, Bank Account / IFSC strings, Transaction Hashes, Case FIR reference IDs, and IP addresses). 
4. **Tabular Numerics**: Set `font-feature-settings: 'tnum' on, 'cv02' on, 'cv03' on, 'cv04' on` across all data tables, analytics panels, and timestamp outputs to ensure columnar alignment.

## Layout & Spacing

The layout model is anchored to an uncompromising 8px baseline grid (with 4px micro-steps for compact data components).

### Layout Geometry
- **Officer Analytical Workspace**: 12-column fluid grid, `1440px` max-width container, with `24px` (`1.5rem`) gutters and `32px` (`2rem`) page outer margins. Density permits side-by-side transaction flow diagrams, live threat tables, and metadata inspection panels.
- **Citizen Verification Surface**: Single-column centered container capped at `768px` max-width, maintaining high focus on the verification input bar and trust score output cards.
- **Mobile Viewport (<768px)**: 4-column layout with `16px` (`1rem`) gutters and `16px` (`1rem`) outer margins. Multi-column tables reflow into discrete forensic card modules.

### Responsive Breakpoints
- **Compact (Mobile)**: `360px` to `767px`
- **Medium (Tablet / Field Handheld)**: `768px` to `1023px`
- **Expanded (Officer Desktop / Command Center)**: `1024px` to `1440px`
- **Ultra-Wide (Wall Monitor / Control Room)**: `>= 1441px`

## Elevation & Depth

To maintain an unyielding light-theme aesthetic, depth is established strictly through **subtle surface tiering**, **frosted optical blurs**, and **ultra-soft, tinted ambient shadows**. Heavy dark drop-shadows and stark black structural borders are prohibited.

### Elevation Levels
1. **Level 0 (Base / Canvas)**: Flat `#F7F8FB` or `#FBF7F1`. No shadow. Zero elevation.
2. **Level 1 (Standard Card / Registry Row)**: Surface `#FFFFFF` with a crisp 1px perimeter outline of `#E2E8F0` or `rgba(15, 23, 42, 0.06)`. Ambient shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.03)`.
3. **Level 2 (Glass Floating Card / Interactive Hover)**: Surface `rgba(255, 255, 255, 0.78)` backed by `backdrop-filter: blur(16px)`. Border `1px solid rgba(15, 23, 42, 0.06)`. Ambient shadow: `0 4px 16px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.03)`.
4. **Level 3 (Modal / Verification Sheet / Dropdown Dock)**: Pure `#FFFFFF` surface with `1px solid rgba(15, 23, 42, 0.08)`. Ambient shadow: `0 20px 25px -5px rgba(15, 23, 42, 0.07), 0 8px 10px -6px rgba(15, 23, 42, 0.03)`. Tinted ambient dispersion ensures the elevation feels weightless and institutional.

## Shapes

The geometric grammar combines approachability for citizens with crisp structure for command staff.

- **Inputs, Buttons, and Identifier Chips**: Standardized to `10px` (`radius-input` / `radius-chip`). This soft contour creates an immediate tactile landing area without drifting into playful toy-like radii.
- **Operational & Intelligence Cards**: Fixed at `16px` (`radius-card`), framing verification summaries, alert containers, and evidence logs with modern precision.
- **Hero Containers & Command Panels**: Fixed at `24px` (`radius-hero`), used exclusively for primary verification banners, citizen guidance blocks, and top-tier state alert dashboards.
- **Avatar Badges & Circular Indicators**: `9999px` (Full circle) strictly reserved for officer profile avatars, trust score dial meters, and pulse status dots.

## Components

### 1. Primary Action & Verification Buttons
- **Primary Police Action**: Solid `#1D4ED8` background, `#FFFFFF` text, `10px` border radius, font `title-md` (`Plus Jakarta Sans` 600). Hover state shifts to `#1E40AF` with a smooth 150ms ease transition. Focus state reveals a `3px` focus ring in `#EEF2FF` with a `1px` `#1D4ED8` outline.
- **Regional / Citizen Highlight Action**: `#E07A2F` background with `#FFFFFF` text. Used for advisory triggers or direct reporting submissions. Hover shifts to `#C2410C`.
- **Secondary / Ghost Button**: White `#FFFFFF` surface, `1px solid #E2E8F0`, `#0F172A` text. Hover transitions to `#F7F8FB` surface with `#1D4ED8` text.

### 2. Search & Identifier Input Fields
- Built for instant copy-pasting of dubious digital signals.
- Height `52px` (Hero search) or `40px` (Table search).
- Background `#FFFFFF`, border `1.5px solid #E2E8F0`, border radius `10px`.
- Left-adorned by dynamic identifier detection glyphs. Monospace font applied automatically upon detection of numeric, hex, or wallet patterns.
- Active focus state: border shifts to `#1D4ED8` with a `0 0 0 3px rgba(29, 78, 216, 0.12)` halo.

### 3. Forensic Identifier Chips & Badges
- Displaying entities (UPI, Phone, Account, Telegram, etc.).
- Height `28px`, radius `10px`, padding `0 10px`.
- Style: Solid 10% tint of the identifier token color as background, matching 100% token color for text and icons.
- Font: `JetBrains Mono` 12px / 500 weight (`label-mono-sm`).
- Always includes interactive copy-to-clipboard action icon on hover.

### 4. Threat & Trust Assessment Cards
- High-level verdict container with `16px` border-radius and `1px` border matching the threat tier.
- Low-Risk Card: Background `#ECFDF5`, border `rgba(5, 150, 105, 0.2)`. Features green checkmark shield icon, bilingual verdict ("विश्वसनीय / Verified Authentic"), and verification timestamp.
- High-Risk Card: Background `#FEF2F2`, border `rgba(220, 38, 38, 0.25)`. Features red alert octagon, explicit warning text ("साइबर अपराध चेतावनी / Cyber Fraud Blacklisted"), FIR association count, and a direct "Report to 1930 / I4C" button.

### 5. Officer Forensic Data Tables
- Header row: `#F7F8FB` background, text `#475569`, 11px uppercase `JetBrains Mono` with subtle bottom border `1px solid #E2E8F0`.
- Data rows: `#FFFFFF` base, height `48px`, alternating subtle hover state `#FBF7F1`.
- Numeric and hash columns use tabular figures (`JetBrains Mono`).
- Inline status tags: Color-coded dot (`8px` diameter) with accompanying textual state indicator.

### 6. Hindi / English Bilingual Display Headers
- Section titles support concurrent script pairing. Primary script rendered in `Plus Jakarta Sans` or `Noto Sans Devanagari` at 20px / 600 weight; secondary language displayed inline or beneath in `#475569` at 14px / 400 weight.