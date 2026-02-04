FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No crear tablas en build; se crearán al iniciar el contenedor (intento tolerante)
# (Se mantiene el archivo create_tables.py para uso en desarrollo)

EXPOSE 8000

CMD ["sh", "-c", "python create_tables.py || true && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]