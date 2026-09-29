FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

WORKDIR /app/website
COPY website/requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt

COPY website/ ./
COPY poetry-display/ /app/poetry-display/
COPY ["Quran+ Poems by Era*/*.txt", "/app/corpora/"]
# Preserve the source directory name, whose final character is a space.
RUN mv /app/corpora "/app/Quran+ Poems by Era "
COPY ["Cross Era Authors Corpus 2000w 2s/metadata.csv", "/app/Cross Era Authors Corpus 2000w 2s/metadata.csv"]
COPY ["القرآن الكريم وتحدي الشعراء ، خوارزمية التجميع الهرمي.mp4", "/app/القرآن الكريم وتحدي الشعراء ، خوارزمية التجميع الهرمي.mp4"]

RUN python -c "from analysis import catalog; from text_metadata import text_metadata; assert len(catalog()) == 12; assert text_metadata()"

USER 10001:10001
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
