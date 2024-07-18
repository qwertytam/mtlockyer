FROM amazon/aws-lambda-python:3.12

# install chrome dependencies
RUN dnf install -y atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel nss mesa-libgbm jq unzip

COPY ./chrome-installer.sh ./chrome-installer.sh
RUN ./chrome-installer.sh
RUN rm ./chrome-installer.sh

RUN pip install selenium

# install other package dependencies
RUN pip install beautifulsoup4

COPY __init__.py ./src/
COPY constants.py ./src/
COPY exceptions.py ./src/
COPY main.py ./src/
COPY objectwrapper.py ./src/
COPY secretswrapper.py ./src/

WORKDIR "/src"
CMD [ "main.lambda_handler" ] 