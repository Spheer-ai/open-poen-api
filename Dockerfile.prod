FROM python:3.11.0
MAINTAINER Spheer.ai <markdewijk@spheer.ai>

RUN echo "Europe/Amsterdam" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y locales

RUN sed -i -e 's/# nl_NL.UTF-8 UTF-8/nl_NL.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales

# Libraries that Weasyprint requires and the font that is used for rendering reports.
RUN apt install -y libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 fonts-open-sans

COPY dist/*.whl /tmp/
COPY dist/requirements.txt /tmp/
COPY auth/ /app/auth/
COPY open_poen_api/main.polar /app/open_poen_api/main.polar
WORKDIR /app

RUN pip install --no-deps -r /tmp/requirements.txt /tmp/*.whl

CMD ["uvicorn", "open_poen_api:app", "--host", "0.0.0.0", "--port", "8000"]