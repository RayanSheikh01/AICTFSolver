FROM kalilinux/kali-rolling

RUN apt-get update && apt-get install -y \
    nmap \
    sqlmap \
    gobuster \
    nikto \
    whatweb \
    hydra \
    hashcat \
    curl \
    python3 \
    python3-pip \
    python3-requests \
    python3-pwntools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# Note: Fixed entrypoint syntax to properly pass CMD arguments
ENTRYPOINT ["/bin/sh", "-c", "mkdir -p /work/raw && exec \"$@\"", "--"]

CMD ["sleep", "infinity"]