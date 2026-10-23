FROM python:3.11-slim

RUN useradd --create-home --uid 1000 appuser
ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HF_HOME=/home/appuser/.cache/huggingface
WORKDIR /home/appuser/app

COPY --chown=appuser:appuser requirements.txt ./
# CPU inference needs no CUDA runtime packages. The regular requirements then
# reuse this installed CPU build of torch.
RUN pip install --no-cache-dir 'torch>=2.3' --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .
USER appuser
# Download into the image as the same user that will run the application.
RUN python cache_models.py
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

EXPOSE 7860
CMD ["sh", "-c", "gunicorn -w 1 -b 0.0.0.0:${PORT:-7860} --timeout 180 app:app"]
