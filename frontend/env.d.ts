/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_URL_BASE_API: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
