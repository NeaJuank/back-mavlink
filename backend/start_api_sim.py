"""Arranca la API con `MAVLINK_DEVICE=SIM` para pruebas locales (SITL/sim).

Uso:
    python backend/start_api_sim.py
"""
import os
import sys
import uvicorn

os.environ['MAVLINK_DEVICE'] = 'SIM'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == '__main__':
    # Lanza la app FastAPI (backend.main:app)
    uvicorn.run('backend.main:app', host='0.0.0.0', port=8000, reload=False)
