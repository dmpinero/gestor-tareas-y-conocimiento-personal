# Frontend — Gestor de Tareas y Conocimiento Personal

SPA Vue 3 + TypeScript + Tailwind CSS. Ver el [README](../README.md) y el
[CONTRIBUTING](../CONTRIBUTING.md) del repositorio para la puesta en marcha
completa y las convenciones del proyecto.

## Scripts

| Comando | Qué hace |
| --- | --- |
| `pnpm dev` | Servidor de desarrollo de Vite (proxy de `/api/v1` al backend local). |
| `pnpm build` | Comprobación de tipos y build de producción. |
| `pnpm lint` | oxlint y ESLint con corrección automática. |
| `pnpm type-check` | Comprobación de tipos con `vue-tsc`. |
| `pnpm test:unit run` | Tests unitarios con Vitest. |
| `pnpm exec playwright test` | Tests e2e (incluida la auditoría de accesibilidad WCAG 2.1 AA). |

## Recomendaciones de IDE

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar).
