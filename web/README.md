# Dysentry Frontend

> **App Name:** Dysentry · **Stack:** React 18 + Vite + Tailwind CSS + shadcn/ui · **Dev Server:** `http://localhost:5173`

React frontend for the Dysentry story creation platform — a serialized short-form story editor with AI-powered scene composition, character management, and automated publishing.

---

## Overview

Dysentry is a **story creation studio** that lets creators and brands produce serialized short-form animated stories with:

- **AI-assisted editing**: Chat-based AI assistant for scene revisions
- **Scene pipeline**: Draft → Review → Approve → Lock workflow
- **Mixed media types**: Video, narrated image, and voice scenes
- **Character management**: Persistent character profiles with reference images
- **Style memory**: Visual consistency across episodes
- **Automated scheduling**: Schedule generation and publishing
- **Social publishing**: YouTube and TikTok integration

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | React 18 |
| **Build Tool** | Vite 6 |
| **Routing** | react-router-dom v6 |
| **Styling** | Tailwind CSS 3 + CSS Variables |
| **UI Library** | shadcn/ui (Radix primitives) |
| **Icons** | Lucide React |
| **State Mgmt** | React Context + TanStack Query |
| **Charts** | Recharts |
| **Animations** | Framer Motion |
| **DnD** | @hello-pangea/dnd |
| **Type Checking** | TypeScript (JSDoc) |

---

## Getting Started

### Prerequisites

- Node.js 18+
- pnpm (recommended) or npm
- StoryForge backend running (default: `http://localhost:3001`)

### Commands

```bash
pnpm install         # Install dependencies
pnpm run dev         # Start dev server (port 5173)
pnpm run build       # Production build → dist/
pnpm run lint        # ESLint check
pnpm run typecheck   # TypeScript checking
pnpm run preview     # Preview production build
```



---

## Project Structure

```
web/
├── index.html                    # HTML entry point
├── vite.config.js                # Vite configuration
├── tailwind.config.js            # Tailwind CSS configuration
├── components.json               # shadcn/ui configuration
├── eslint.config.js              # ESLint flat config
├── jsconfig.json                 # TypeScript checking config
├── package.json                  # Dependencies
├── AGENTS.md / CLAUDE.md         # Agent instructions
├── dist/                         # Production build output
└── src/
    ├── main.jsx                  # React entry point
    ├── App.jsx                   # Root component with routing
    ├── index.css                 # Global styles + CSS variables
    ├── api/
    │   ├── base44Client.js       # HTTP client (fetch wrapper)
    │   └── dysentryClient.js     # Domain API mappings
    ├── lib/
    │   ├── AuthContext.jsx       # Auth state provider
    │   ├── app-params.js         # App parameter utilities
    │   ├── query-client.js       # TanStack Query config
    │   └── utils.js              # cn() helper
    ├── pages/
    │   ├── Landing.jsx           # Marketing landing page
    │   ├── Login.jsx             # Login form
    │   ├── Register.jsx          # Registration form
    │   ├── ForgotPassword.jsx    # Password reset request
    │   ├── ResetPassword.jsx     # Password reset with token
    │   ├── Dashboard.jsx         # Stories overview dashboard
    │   ├── Editor.jsx            # Story scene editor
    │   ├── Schedule.jsx          # Scheduled jobs management
    │   └── Settings.jsx          # Account & connections
    └── components/
        ├── ui/                   # shadcn/ui components (50+)
        ├── AuthLayout.jsx        # Auth page layout
        ├── ProtectedRoute.jsx    # Auth guard
        └── dysentry/             # App-specific components
            ├── AppChrome.jsx     # Authenticated app shell
            ├── SiteChrome.jsx    # Public site shell
            ├── CreateStoryModal.jsx  # Story creation dialog
            ├── editor/
            │   ├── AiChatPanel.jsx, SceneList.jsx
            │   ├── SceneStage.jsx, CharacterSheet.jsx
            │   └── ExportMenu.jsx, StyleMemoryDialog.jsx
            └── schedule/
                ├── ScheduleForm.jsx
                └── ScheduledJobCard.jsx
```

---

## Pages & Routing

Routes are defined in `src/App.jsx`:

| Path | Page | Auth | Description |
|---|---|---|---|
| `/` | `Landing` | No | Public marketing |
| `/login` | `Login` | No | Email/password login |
| `/register` | `Register` | No | Registration |
| `/forgot-password` | `ForgotPassword` | No | Password reset request |
| `/reset-password` | `ResetPassword` | No | Reset with token |
| `/dashboard` | `Dashboard` | Yes | Story overview |
| `/editor/:seriesId` | `Editor` | Yes | Story scene editor |
| `/schedule` | `Schedule` | Yes | Automation schedules |
| `/settings` | `Settings` | Yes | Account & connections |

Protected routes are wrapped in `<AuthenticatedApp />` which checks auth via `AuthContext` and redirects to `/login` if unauthenticated.

---

## API Layer

### `base44Client.js` — HTTP Client

- Auto-attaches `Bearer` token from `localStorage`
- Emits `dysentry:auth-error` event on 401/403
- Exposes `db.entities` with CRUD methods for all backend resources
- Auth methods: login, register, logout, me, isAuthenticated

### `dysentryClient.js` — Domain API

Domain-specific functions with data mapping (`mapStoryToSeries`, `mapSceneToEditorScene`, etc.):
- `listStories()`, `getEditorStory(id)`, `getDashboardBatch(ids)`
- `listEditorEpisodes(id)`, `listEditorScenes(storyId, episodeId)`
- `createEditorScene()`, `regenerateEditorScene()`, `approveEditorScene()`
- `createSchedule()`, `listSchedules()`, `deleteSchedule()`
- `createCharacter()`, `updateCharacter()`, `deleteCharacter()`
---

## Editor Architecture

The Editor at `/editor/:seriesId` uses a **3-column layout**:

| Column | Component | Purpose |
|---|---|---|
| Left (280px) | `SceneList` | Scene sidebar with status indicators |
| Center (flex) | `SceneStage` | Main editing panel (media preview, script, narration) |
| Right (340px) | `AiChatPanel` | AI assistant chat with scene patching |

### Scene Status Flow

```
Draft → Request Review → Pending Review → Approve → Approved → Lock → Locked
```

### Key Features

- **AI Assistant**: Context-aware chat that can generate scene patches (title, script, narration, visual prompt) and apply them to current scene or create new scenes
- **Character Sheet**: Slide-out panel for managing character profiles
- **Style Memory**: Dialog for visual style notes (persisted to `pipeline_config`)
- **Media Preview**: Displays generated video/image or placeholder

---

## Key Components

| Component | Description |
|---|---|
| `AppChrome` | Authenticated shell: sidebar nav + header breadcrumb + main area |
| `SiteChrome` | Public shell: announcement bar + navbar + footer |
| `CreateStoryModal` | Form dialog: title, prompt, workflow type, genre, style, ratio, episodes/scenes |
| `Dashboard` | Summary cards, pipeline runs, schedules, story grid, episode chart |
| `SceneList` | Scene order list with drag handle, status badges, action dropdown |
| `SceneStage` | Scene title, media preview, type selector, script/narration/notes editors |
| `AiChatPanel` | Chat messages, context display, apply-patch / new-scene buttons |
| `CharacterSheet` | Character list, add/edit/delete, role badges, detail dialog |
| `SchedulePage` | Schedule list with status, create form dialog, cancel action |
| `SettingsPage` | Account info, platform connections (YouTube, TikTok) |

---

## Styling & Theming

### Design Tokens (Monochrome + Blue)

```css
--color-ink: #1e242c;           /* Dark text */
--color-steel: #576579;         /* Muted text */
--color-paper: #ffffff;         /* Background */
--color-mist: #e7eaee;          /* Subtle borders */
--color-fog: #dbdfe5;           /* Borders */
--color-signal-blue: #1a73e8;   /* Primary accent */
```

### Typography

- **Display/Headings**: `Inter Tight` (tight letter-spacing)
- **Body**: `Inter`
- **Mono**: System monospace

### Tailwind Config

- Dark mode via `class` strategy
- Custom colors, fonts, shadows, animations
- shadcn/ui integration with `tailwindcss-animate`

---

## Authentication Flow

1. On load, `AuthContext` checks `localStorage` for token
2. If token exists → calls `GET /pipeline/auth/me` to validate
3. If valid → protected routes render; if 401 → token cleared → redirect to `/login`
4. API 401/403 responses emit custom events that trigger auto-logout
5. Login: email/password → token stored → redirect to `/dashboard`
6. Register: auto-login on success → redirect to `/dashboard`

---

## Build & Deployment

```bash
pnpm run build        # Output: web/dist/
pnpm run preview      # Preview production build
```

For one-deployment model, the backend (`alibaba_entry.py`) serves `dist/` files as static assets.

---

## Code Quality

- **ESLint** with React and React Hooks plugins
- **Unused imports** flagged as errors
- **TypeScript checking** via JSDoc (`pnpm run typecheck`)
- **Lint fix**: `pnpm run lint:fix`
