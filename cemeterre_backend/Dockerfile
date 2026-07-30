FROM python:3.13-slim

# Librairies système nécessaires pour GDAL/GEOS/PROJ (GeoDjango)
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Variables pour que Django trouve GDAL sur Linux (chemins standards Debian)
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD bash -c "python manage.py migrate --noinput && gunicorn cemeterre_backend.wsgi:application --bind 0.0.0.0:\$PORT"