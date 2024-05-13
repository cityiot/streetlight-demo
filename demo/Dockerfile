# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

# FROM python:3.6
FROM nikolaik/python-nodejs:python3.6-nodejs10
RUN pip install --upgrade pip

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

# install the required Python libraries
COPY requirements.txt ./
RUN pip install -r requirements.txt

# install the required NodeJS libraries
# NOTE: these are used with repng
RUN mkdir -p nodejs
COPY package.json ./nodejs
WORKDIR /usr/src/app/nodejs
RUN npm install

# Install latest chrome dev package and fonts to support major charsets (Chinese, Japanese, Arabic, Hebrew, Thai and a few others)
# Note: this installs the necessary libs to make the bundled version of Chromium that Puppeteer installs, work.
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y google-chrome-unstable fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst fonts-freefont-ttf \
       --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN npm install puppeteer@2.0.0

# Install the repng nodeJS scripts that can be used to make png images from React components using puppeteer.
RUN git clone https://github.com/SindreSvendby/repng.git repng
RUN cp repng/index.js .
RUN cp repng/cli.js .
COPY react_scripts/ ./

# Install the wait-for-it script that is used to start the program only when the database is available.
WORKDIR /usr/src/app
RUN git clone https://github.com/vishnubob/wait-for-it.git
RUN chmod +x ./wait-for-it/wait-for-it.sh

# Copy the program files to the image.
COPY js_resources.txt .
COPY manage.py .
COPY start_demo.sh .
COPY demo/ ./demo/
COPY env/ ./env/
COPY streetlight/ ./streetlight
RUN chmod +x start_demo.sh

EXPOSE 8000
CMD ["python", "-u", "-m", "manage", "runserver", "0.0.0.0:8000"]
