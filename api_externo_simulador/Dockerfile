# Dockerfile para el Banco Simulado Externo
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema si son necesarias
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear usuario no-root para seguridad
RUN adduser --disabled-password --gecos '' bankuser && \
    chown -R bankuser:bankuser /app
USER bankuser

# Exponer el puerto
EXPOSE 5001

# Variables de entorno por defecto
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar la aplicación
CMD ["python", "main.py"]