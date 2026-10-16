# VeraAgent frontend

React and TypeScript UI for the VeraAgent desktop app. Vite proxies `/api` to `http://127.0.0.1:8000` during development; desktop builds embed the API base URL explicitly.

```powershell
npm ci
npm run dev
```

Run `npm run lint` and `npm run build` before submitting UI changes. See the repository-level [development guide](../docs/DEVELOPMENT.md) and [testing guide](../docs/TESTING.md).
