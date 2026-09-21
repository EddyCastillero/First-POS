# Usamos una imagen oficial y ligera de Python
FROM python:3.11-slim

# Definimos la carpeta interna del contenedor (la parte de la "derecha")
WORKDIR /app

# Copiamos primero las dependencias para aprovechar el caché
COPY requirements.txt .

# Instalamos las librerías
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de tu código (aunque en desarrollo local esto se sobrescribe por tu volumen)
COPY . .

# Comando por defecto (en Compose lo sobrescribimos con --reload para desarrollo)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]