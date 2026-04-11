# Phase 8 — Frontend Scaffolding + Design Tokens

프론트엔드는 Phase 0에서 SvelteKit 빈 스캐폴드로 초기화됐다. 이 페이즈에서는 Tailwind 설정, 디자인 토큰, 공통 프리미티브(Button, Input 등)를 갖춘 뒤 실제 화면 구현의 토대를 만든다.

**사전 조건**: Phase 0.3 완료 (SvelteKit + Vite + TypeScript 기본 구조).

---

### Task 8.1: Tailwind CSS 설정 + 디자인 토큰

**Files:**
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.js`
- Modify: `frontend/src/app.css`

- [ ] **Step 1: postcss.config.js 작성**

Write `frontend/postcss.config.js`:

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {}
  }
};
```

- [ ] **Step 2: tailwind.config.js 작성 (디자인 토큰 포함)**

Write `frontend/tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '"Pretendard Variable"',
          '-apple-system',
          '"SF Pro Display"',
          'system-ui',
          'sans-serif'
        ]
      },
      colors: {
        bg: {
          light: '#F9FAFB',
          dark: '#000000'
        },
        surface: {
          light: '#FFFFFF',
          dark: '#1C1C1E',
          'dark-elevated': '#2C2C2E'
        },
        text: {
          primary: {
            light: '#191F28',
            dark: '#FFFFFF'
          },
          secondary: {
            light: '#6B7684',
            dark: '#98989F'
          }
        },
        divider: {
          light: '#F2F4F6',
          dark: 'rgba(255,255,255,0.06)'
        },
        brand: {
          DEFAULT: '#3182F6',
          pressed: '#1B64DA',
          dark: '#4C9AFF'
        },
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#FF5847'
      },
      borderRadius: {
        card: '20px',
        button: '14px',
        input: '12px',
        badge: '8px'
      },
      boxShadow: {
        card: '0 1px 2px rgba(20,20,43,0.04), 0 12px 40px rgba(20,20,43,0.06)'
      },
      fontSize: {
        display: ['42px', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '700' }],
        title: ['24px', { lineHeight: '1.3', fontWeight: '700' }],
        body: ['17px', { lineHeight: '1.55', fontWeight: '400' }],
        caption: ['13px', { lineHeight: '1.4', fontWeight: '500' }]
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.2, 0.9, 0.2, 1.05)'
      }
    }
  },
  plugins: []
};
```

- [ ] **Step 3: app.css 확장 (Tailwind 지시자 + 기본 리셋)**

Overwrite `frontend/src/app.css`:

```css
@import '@fontsource-variable/pretendard';

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    font-family: 'Pretendard Variable', -apple-system, 'SF Pro Display', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    overscroll-behavior: contain;
  }

  body {
    @apply bg-bg-light text-text-primary-light;
    font-feature-settings: 'ss01', 'ss02';
  }

  html.dark body {
    @apply bg-bg-dark text-text-primary-dark;
  }

  * {
    font-variant-numeric: tabular-nums;
  }
}

@layer components {
  .card {
    @apply bg-surface-light rounded-card shadow-card;
  }
  html.dark .card {
    @apply bg-surface-dark border border-divider-dark shadow-none;
  }
  .btn-primary {
    @apply inline-flex items-center justify-center bg-brand text-white
           rounded-button h-14 px-6 font-semibold text-body
           transition active:scale-[0.97];
  }
  .btn-primary:hover {
    @apply bg-brand-pressed;
  }
}
```

- [ ] **Step 4: 빌드 검증**

Run:
```bash
cd frontend
npm run build
```
Expected: 에러 없이 빌드 완료.

- [ ] **Step 5: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/postcss.config.js frontend/tailwind.config.js frontend/src/app.css
git commit -m "feat(frontend): add Tailwind + GenSub design tokens"
```

---

### Task 8.2: 다크 모드 감지 유틸

**Files:**
- Create: `frontend/src/lib/theme.ts`

- [ ] **Step 1: theme 유틸 작성**

Write `frontend/src/lib/theme.ts`:

```typescript
import { writable } from 'svelte/store';

type Theme = 'light' | 'dark';

const STORAGE_KEY = 'gensub.theme';

function detect(): Theme {
  if (typeof window === 'undefined') return 'light';
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function apply(theme: Theme) {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

export const theme = writable<Theme>('light');

export function initTheme() {
  const initial = detect();
  theme.set(initial);
  apply(initial);
  theme.subscribe((t) => {
    apply(t);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, t);
    }
  });
}

export function toggleTheme() {
  theme.update((t) => (t === 'light' ? 'dark' : 'light'));
}
```

- [ ] **Step 2: layout에서 초기화**

Overwrite `frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { initTheme } from '$lib/theme';

  onMount(() => {
    initTheme();
  });
</script>

<slot />
```

- [ ] **Step 3: 빌드 검증**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 4: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/theme.ts frontend/src/routes/+layout.svelte
git commit -m "feat(frontend): add theme store with system detection and toggle"
```

---

### Task 8.3: Button 프리미티브

**Files:**
- Create: `frontend/src/lib/ui/Button.svelte`

- [ ] **Step 1: Button 컴포넌트 작성**

Write `frontend/src/lib/ui/Button.svelte`:

```svelte
<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'ghost' = 'primary';
  export let disabled = false;
  export let type: 'button' | 'submit' = 'button';
  export let fullWidth = false;

  const variantClass: Record<string, string> = {
    primary:
      'bg-brand text-white hover:bg-brand-pressed dark:bg-brand-dark dark:hover:bg-brand',
    secondary:
      'bg-surface-light text-text-primary-light dark:bg-surface-dark dark:text-text-primary-dark border border-divider-light dark:border-divider-dark',
    ghost:
      'bg-transparent text-text-secondary-light hover:text-text-primary-light dark:text-text-secondary-dark dark:hover:text-text-primary-dark'
  };
</script>

<button
  {type}
  {disabled}
  on:click
  class="inline-flex items-center justify-center h-14 px-6 rounded-button font-semibold text-body
         transition-all ease-spring active:scale-[0.97]
         disabled:opacity-50 disabled:cursor-not-allowed
         {variantClass[variant]}
         {fullWidth ? 'w-full' : ''}"
>
  <slot />
</button>
```

- [ ] **Step 2: 빌드 검증**

Run: `cd frontend && npm run check && npm run build`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/Button.svelte
git commit -m "feat(frontend): add Button primitive"
```

---

### Task 8.4: Input 프리미티브

**Files:**
- Create: `frontend/src/lib/ui/Input.svelte`

- [ ] **Step 1: Input 컴포넌트 작성**

Write `frontend/src/lib/ui/Input.svelte`:

```svelte
<script lang="ts">
  export let value = '';
  export let placeholder = '';
  export let type: 'text' | 'url' = 'text';
  export let disabled = false;
  export let id: string | undefined = undefined;
  export let autofocus = false;
</script>

<input
  {id}
  {type}
  {placeholder}
  {disabled}
  bind:value
  on:input
  on:change
  on:keydown
  {autofocus}
  class="w-full bg-transparent border-0 border-b-2 border-divider-light dark:border-divider-dark
         py-4 text-display text-text-primary-light dark:text-text-primary-dark
         placeholder:text-text-secondary-light dark:placeholder:text-text-secondary-dark
         focus:border-brand focus:outline-none transition-colors"
/>
```

- [ ] **Step 2: 빌드 검증**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/Input.svelte
git commit -m "feat(frontend): add Input primitive (Toss-style underline)"
```

---

### Task 8.5: Segmented Control 프리미티브

**Files:**
- Create: `frontend/src/lib/ui/Segmented.svelte`

- [ ] **Step 1: 컴포넌트 작성**

Write `frontend/src/lib/ui/Segmented.svelte`:

```svelte
<script lang="ts">
  type Option = { value: string; label: string };
  export let options: Option[] = [];
  export let value: string;
</script>

<div
  class="inline-flex items-center p-1 rounded-xl bg-divider-light dark:bg-surface-dark-elevated gap-1"
  role="tablist"
>
  {#each options as opt}
    <button
      type="button"
      role="tab"
      aria-selected={value === opt.value}
      on:click={() => (value = opt.value)}
      class="px-4 py-2 text-caption font-semibold rounded-lg transition-all ease-spring
             {value === opt.value
               ? 'bg-surface-light dark:bg-surface-dark text-text-primary-light dark:text-text-primary-dark shadow-sm'
               : 'text-text-secondary-light dark:text-text-secondary-dark'}"
    >
      {opt.label}
    </button>
  {/each}
</div>
```

- [ ] **Step 2: 빌드 검증**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/Segmented.svelte
git commit -m "feat(frontend): add iOS-style segmented control"
```

---

### Task 8.6: Circular Progress 컴포넌트

**Files:**
- Create: `frontend/src/lib/ui/CircularProgress.svelte`

- [ ] **Step 1: 컴포넌트 작성**

Write `frontend/src/lib/ui/CircularProgress.svelte`:

```svelte
<script lang="ts">
  import { tweened } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';

  export let value = 0; // 0.0 ~ 1.0
  export let size = 140;
  export let stroke = 8;

  const tweenedValue = tweened(value, { duration: 400, easing: cubicOut });
  $: tweenedValue.set(Math.max(0, Math.min(1, value)));

  $: radius = (size - stroke) / 2;
  $: circumference = 2 * Math.PI * radius;
  $: offset = circumference * (1 - $tweenedValue);
  $: percentText = Math.round($tweenedValue * 100);
</script>

<div class="relative flex items-center justify-center" style="width:{size}px; height:{size}px">
  <svg width={size} height={size} class="-rotate-90">
    <circle
      cx={size / 2}
      cy={size / 2}
      r={radius}
      fill="none"
      class="stroke-divider-light dark:stroke-surface-dark-elevated"
      stroke-width={stroke}
    />
    <circle
      cx={size / 2}
      cy={size / 2}
      r={radius}
      fill="none"
      class="stroke-brand dark:stroke-brand-dark"
      stroke-width={stroke}
      stroke-linecap="round"
      stroke-dasharray={circumference}
      stroke-dashoffset={offset}
      style="transition: stroke-dashoffset 400ms cubic-bezier(0.2, 0.9, 0.2, 1.05)"
    />
  </svg>
  <div class="absolute text-display font-bold">
    {percentText}
    <span class="text-title text-text-secondary-light dark:text-text-secondary-dark">%</span>
  </div>
</div>
```

- [ ] **Step 2: 빌드 검증**

Run: `cd frontend && npm run build`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd /Users/loki/GenSub
git add frontend/src/lib/ui/CircularProgress.svelte
git commit -m "feat(frontend): add circular progress indicator"
```

---
