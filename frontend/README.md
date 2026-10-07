# LIFEGRID Frontend

React/Vite emergency operations UI for the local LIFEGRID API. The map and charts use Leaflet/OpenStreetMap and Recharts. All current report and resource fixtures are synthetic.

Start the FastAPI backend from the repository root:

```powershell
python -m uvicorn backend.main:app --reload
```

Then from `frontend/`:

```powershell
npm install
npm run dev
```

The Vite app binds to `http://127.0.0.1:5173`. Configure `VITE_API_BASE_URL` in `.env.local` if the local API uses another URL; its default is `http://127.0.0.1:8000`. The FastAPI CORS origin is configured by `LIFEGRID_FRONTEND_ORIGIN`.

Run `npm run lint` and `npm run build` for local checks. No AWS credentials, services, or cloud resources are used by the frontend.