FROM python:3.12-slim

ARG DENO_VERSION=2.5.6

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl ffmpeg unzip \
    && curl -fsSL "https://github.com/denoland/deno/releases/download/v${DENO_VERSION}/deno-x86_64-unknown-linux-gnu.zip" -o /tmp/deno.zip \
    && unzip /tmp/deno.zip -d /usr/local/bin \
    && rm -rf /var/lib/apt/lists/* /tmp/deno.zip \
    && useradd --system --uid 10001 --create-home bot \
    && install -d -o bot -g bot /app /var/lib/snatchvideo-bot/tmp

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=bot:bot . .

USER bot
CMD ["python", "bot.py"]
