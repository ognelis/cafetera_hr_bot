---
trigger: glob
glob: templates/**/*.html, static/**/*.css
---
# Admin UI Design

## Purpose

This project uses a restrained **enterprise admin UI** style.

This rule defines the default visual direction for all server-rendered templates.
Use it together with frontend architecture rules.

If a task includes a screenshot or explicit design prompt, follow that task-specific direction first.
Otherwise, use the rules below.

***

## Design direction

Target style:

- clean
- calm
- neutral
- structured
- data-first
- compact but readable
- modern without decorative excess

The UI should feel like a real internal tool used every day.

Prefer:
- clarity over novelty
- consistency over visual experimentation
- hierarchy over decoration
- maintainability over cleverness

***

## Layout

Use practical admin layouts.

Rules:
- prefer stable page structure
- keep page headers compact
- keep controls close to the content they affect
- the main work surface should usually be a table, list, form, or detail panel
- avoid giant empty areas
- avoid oversized cards and oversized spacing
- use compact-to-medium spacing rhythm

Admin pages are not landing pages.

***

## Hierarchy

Use restrained hierarchy.

Recommended defaults:
- page title: `text-xl font-semibold`
- helper/subtitle: `text-sm text-base-content/60`
- section title: `text-sm font-medium`
- primary row label: `font-medium`
- metadata: `text-sm text-base-content/60`
- tertiary hints: `text-xs text-base-content/50`

Do not use:
- hero sections
- giant headings
- display typography
- marketing-style intro blocks

***

## Surfaces

Use subtle depth.

Rules:
- prefer borders and soft surface contrast over heavy shadows
- use cards only when grouping is actually helpful
- keep containers clean and quiet
- use moderate radii
- prefer `rounded-md` and `rounded-lg`

Avoid:
- glow
- glassmorphism
- decorative gradients
- very large rounded corners everywhere
- strong shadows on every block

***

## Color

Use color sparingly.

Rules:
- keep the interface mostly neutral
- use one restrained primary accent
- use semantic color only for status, focus, destructive, and key actions
- keep secondary information muted

Do not:
- make every element colorful
- use too many badge colors
- use color as decoration
- turn the interface into a bright SaaS dashboard

***

## Tables and lists

Tables and structured lists are the primary work surface in admin UI.

Rules:
- optimize for scanability
- keep rows compact and readable
- use subtle row separators
- make the main entity visually primary
- keep metadata secondary
- keep actions compact and aligned
- hover states should be visible but restrained

Do not:
- replace tables with large cards unless explicitly needed
- overload rows with badges, icons, and buttons
- make row actions too prominent
- use decorative row styling

***

## Controls

Controls should feel compact and operational.

Rules:
- prefer `btn-sm`, compact inputs, and compact selects for admin pages
- use one clear primary action per area
- secondary actions should be quieter
- destructive actions should be recognizable but not dominant
- icon buttons must have `aria-label`

Do not:
- use many competing primary buttons
- make destructive controls visually loud by default
- oversize toolbar controls

***

## Empty and loading states

States must feel intentional.

Rules:
- never leave data areas blank
- always provide empty states
- always provide loading feedback for server actions
- skeletons should resemble final layout
- empty states should be calm and practical

Prefer neutral iconography over emoji in polished product screens.

***

## DaisyUI usage

DaisyUI is the baseline, not the final look.

Rules:
- start with DaisyUI components
- refine with Tailwind utilities for spacing, density, borders, hierarchy, and alignment
- do not ship raw default component styling if it looks too generic or too playful
- do not add custom CSS when DaisyUI already solves the problem
- use small targeted overrides only when needed

***

## Do not

Do not:
- make admin pages look like landing pages
- center everything
- use hero sections in internal tools
- use giant spacing
- use oversized typography
- use heavy decorative cards
- use many bright colors
- use glow, glass, neon, or promo-style gradients
- use emoji-heavy polished UI
- make the page look like a generic AI-generated SaaS template

When in doubt, choose the option that is calmer, clearer, denser, more consistent, easier to maintain, and better for daily work. If the result feels like a serious back-office tool, the direction is probably correct. If it feels like a startup marketing page, it is wrong.