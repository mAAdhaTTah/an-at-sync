FROM python:3.12.1 as build

LABEL name="an-at-sync" \
  maintainer="James DiGioia <jamesorodig@gmail.com>" \
  description="Python package & cli for syncing between ActionNetwork & AirTable" \
  homepage="https://github.com/mAAdhaTTah/an-at-sync" \
  documentation="https://github.com/mAAdhaTTah/an-at-sync/blob/main/README.md"

WORKDIR /app

COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12.1 as app

ENV PYTHONPATH /app
# System-level base config
ENV \
  LANGUAGE=en_US:en \
  LC_ALL=C.UTF-8 \
  LANG=C.UTF-8 \
  PYTHONIOENCODING=UTF-8 \
  PYTHONUNBUFFERED=1

COPY --from=build /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=build /usr/local/bin /usr/local/bin

WORKDIR /app

COPY ./an_at_sync an_at_sync

EXPOSE 8080

CMD ["uvicorn", "an_at_sync.wsgi:wsgi", "--host", "0.0.0.0", "--port", "80"]
