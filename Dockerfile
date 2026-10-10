FROM debian:trixie-slim

#TODO:
# - Fix container build
# - Handle config
# - Handle storage device attachment
# - Handle any buses / GPIO required
# - Actually test any of this

#DEBUG: Install via apt instead of pip
#RUN echo -e "Enabled: yes\nTypes: deb\nURIs: http://archive.raspberrypi.com/debian/\nSuites: trixie\nComponents: main\nSigned-By: /usr/share/keyrings/raspberrypi-archive-keyring.pgp" > /etc/apt/sources.list.d/raspi.sources
#RUN mkdir -p /usr/share/keyrings
#COPY raspberrypi-archive-keyring.pgp /usr/share/keyrings/raspberrypi-archive-keyring.pgp
#RUN apt update
#RUN apt install -y python3 python3-picamera2 --no-install-recommends
#RUN apt clean

RUN apt update \
    && apt install -y python3 python3-pip --no-install-recommends \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

#DEBUG: Potential dependencies
RUN apt install -y build-essential --no-install-recommends

#DEBUG: Potential dependencies
#RUN apt install -y python3-numpy python3-piexif python3-pillow ninja-build cmake make patchelf gcc --no-install-recommends

RUN pip install --break-system-packages --no-cache-dir picamera2

COPY app /cellular-automata

CMD ["python3", "app/dashcam.py"]
