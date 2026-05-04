---
name: <archetype-id>
description: <one-line description of what this archetype covers>
domain-indicators:
  - <keyword1>
  - <keyword2>
  - <keyword3>
---

# Archetype: <Human-Readable Name>

This file defines the visual conventions, icon mappings, connection semantics, and layout preferences for **<domain>** architecture diagrams in the architecture designer application.

## Layer Conventions

Define the layer categories that appear in diagrams of this domain. Each layer groups related components and uses a distinct color pair for visual separation.

| Layer Category | Purpose | Background | Border |
|---------------|---------|------------|--------|
| _Category name_ | _What components belong here_ | `#hex6` | `#hex6` |

## Icon Mappings

Map domain concepts to Lucide icon names. Invalid icon names default to `Database`.

Available Lucide icons:

`Activity`, `Archive`, `BarChart`, `Bell`, `Box`, `Cable`, `Cloud`, `CloudCog`, `Code`, `Cog`, `Container`, `Cpu`, `Database`, `DatabaseZap`, `FileCode`, `Fingerprint`, `Folder`, `GitBranch`, `Globe`, `HardDrive`, `Key`, `Laptop`, `Layers`, `Lock`, `Mail`, `Monitor`, `Network`, `Plug`, `Radio`, `Router`, `Server`, `ServerCog`, `Shield`, `ShieldCheck`, `Smartphone`, `Tablet`, `Terminal`, `User`, `Users`, `Wifi`, `Zap`

| Domain Concept | Icon | Notes |
|---------------|------|-------|
| _Concept_ | `IconName` | _When to use this icon_ |

## Connection Semantics

Define the color language for connections. Each flow type gets a distinct color so readers can visually trace different kinds of data movement.

| Flow Type | Color | Meaning |
|-----------|-------|---------|
| _Flow type_ | `#hex6` (_color name_) | _What this flow represents_ |

## Layout Preferences

Domain-specific layout guidance that supplements the universal spacing rules.

- **Primary flow direction:** _top-to-bottom | left-to-right | radial_
- **Density:** _sparse | moderate | dense_
- **Emphasis:** _what the eye should be drawn to first_
- **Special rules:** _any domain-specific layout considerations_
