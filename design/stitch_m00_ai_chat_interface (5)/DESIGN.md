---
name: Futuristic AI Chatbot Interface
colors:
  surface: '#131315'
  surface-dim: '#131315'
  surface-bright: '#39393b'
  surface-container-lowest: '#0e0e10'
  surface-container-low: '#1c1b1d'
  surface-container: '#201f21'
  surface-container-high: '#2a2a2c'
  surface-container-highest: '#353437'
  on-surface: '#e5e1e4'
  on-surface-variant: '#bec8d2'
  inverse-surface: '#e5e1e4'
  inverse-on-surface: '#313032'
  outline: '#88929b'
  outline-variant: '#3e4850'
  surface-tint: '#89ceff'
  primary: '#89ceff'
  on-primary: '#00344d'
  primary-container: '#0ea5e9'
  on-primary-container: '#003751'
  inverse-primary: '#006591'
  secondary: '#adc6ff'
  on-secondary: '#002e6a'
  secondary-container: '#0566d9'
  on-secondary-container: '#e6ecff'
  tertiary: '#bcc7de'
  on-tertiary: '#263143'
  tertiary-container: '#919cb2'
  on-tertiary-container: '#293446'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c9e6ff'
  primary-fixed-dim: '#89ceff'
  on-primary-fixed: '#001e2f'
  on-primary-fixed-variant: '#004c6e'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#d8e3fb'
  tertiary-fixed-dim: '#bcc7de'
  on-tertiary-fixed: '#111c2d'
  on-tertiary-fixed-variant: '#3c475a'
  background: '#131315'
  on-background: '#e5e1e4'
  surface-variant: '#353437'
typography:
  headline-xl:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  code:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter-sm: 0.75rem
  gutter-md: 1.5rem
  margin-page: 2rem
  sidebar-width: 280px
  chat-max-width: 768px
---

## Brand & Style

This design system is tailored for a cutting-edge, professional AI chatbot interface targeting developers, technical architects, and power users. The aesthetic merges **Minimalism** with subtle **Glassmorphism**, creating a quiet, focused environment that reduces cognitive load during intense coding or analytical sessions. 

The emotional response is precise, high-performance, and trustworthy. The interface feels weightless yet grounded, utilizing translucent layers and electric accents to signal active computational intelligence without visual clutter.

## Colors

The color architecture is built on a hyper-dark foundation to maximize contrast for code blocks and data visualizations. 

- **Primary (`#0ea5e9`):** Electric cyan used for active states, primary actions, and focus indicators.
- **Secondary (`#3b82f6`):** Vibrant cobalt blue reserved for gradients, interactive highlights, and secondary branding moments.
- **Tertiary (`#1e293b`):** Deep slate/navy used for elevated surfaces, container backgrounds, and subtle component grouping.
- **Neutral (`#0a0a0c`):** The absolute dark void background that anchors the interface and makes luminescent elements pop.

## Typography

The typography system pairs a clean, minimalist sans-serif for UI chrome and conversational text with a precise monospaced font for code outputs, metadata, and micro-labels. 

- **Geist** serves as the primary engine for all headings and body copy, offering exceptional legibility at small sizes and a modern technical voice.
- **JetBrains Mono** is utilized strictly for code blocks, terminal outputs, tokens, and technical telemetry to reinforce the developer-centric focus.
- Ensure line heights remain tight yet breathable. Headings employ negative letter spacing to project authority and precision.

## Layout & Spacing

The layout relies on a **fluid grid** combined with a strict 4px/8px spatial rhythm. The application shell is divided into a collapsible navigation sidebar, a central conversation canvas, and optional context inspectors.

- **Breakpoints:** Mobile (`< 768px`), Tablet (`768px - 1024px`), Desktop (`> 1024px`).
- **Chat Canvas:** The core chat feed constrains its maximum width to ensure optimal reading line lengths, floating centrally with generous horizontal breathing room.
- **Spacing Scale:** Leverage 4px increments for micro-padding (badges, inputs) and 16px/24px increments for macro-layout separation (panels, cards).

## Elevation & Depth

Depth is achieved primarily through **soft glassmorphism** and **low-contrast outlines** rather than heavy drop shadows. 

- **Surface Tiering:** Use semi-transparent dark navy surfaces (`#1e293b` at 60–80% opacity) paired with a `12px` backdrop blur to separate floating elements (command palettes, dropdowns, sticky headers) from the pitch-black background.
- **Borders:** Define spatial boundaries using ultra-thin, low-opacity blue-gray borders (`rgba(59, 130, 246, 0.15)`). 
- **Glows:** For active AI states or primary buttons, apply a subtle, diffused outer glow using the primary electric blue (`0 0 20px rgba(14, 165, 233, 0.15)`) to simulate internal luminescence.

## Shapes

The interface embraces a **Rounded** shape language, striking a balance between futuristic precision and approachable ergonomics.

- **Base Radius:** Standard UI elements (buttons, inputs, dropdowns) use a `0.5rem` (8px) corner radius.
- **Containers & Cards:** Large surfaces, chat bubbles, and modals scale up to `1rem` (16px) or `1.5rem` (24px) for a softer, contemporary container feel.
- **Pills & Badges:** Status indicators, tags, and code language markers use full pill shapes (`9999px`) to create clear, enclosed visual islands.

## Components

- **Buttons:** Primary actions feature a vibrant electric blue gradient background with crisp typography and an optional hover glow. Secondary buttons use ghost styling with translucent dark surfaces and subtle borders.
- **Input Fields:** The core prompt input acts as the hero component of the screen—a wide, pill-ish or softly rounded container featuring a frosted glass background, inner shadow, and an integrated toolbar for attachments and model selection.
- **Chat Bubbles:** User messages are rendered in solid dark slate containers aligned to the right. AI responses blend seamlessly into the background canvas with no solid container, distinguished solely by avatar placement and markdown formatting.
- **Code Blocks:** Embedded within AI responses, code blocks feature a deep black-navy background, JetBrains Mono typography, a subtle blue-gray border, and a floating copy-to-clipboard action in the top-right corner.
- **Chips & Tags:** Compact pill elements used for prompt suggestions or model parameters, utilizing a faint blue-tinted background and hover state that shifts to solid primary border.
- **Lists & Navigation:** Sidebar navigation items utilize subtle left-border accent indicators on active states rather than heavy background fills, keeping the directory clean and unobtrusive.