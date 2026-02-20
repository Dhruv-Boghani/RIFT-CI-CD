# Base Image
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update and install common tools
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    openssh-client \
    build-essential \
    software-properties-common \
    unzip \
    jq \
    && rm -rf /var/lib/apt/lists/*

# --- Python 3.10+ ---
RUN apt-get update && apt-get install -y python3 python3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python

# --- Node.js 20 ---
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# --- Java (OpenJDK 17) & Maven & Gradle ---
RUN apt-get update && apt-get install -y openjdk-17-jdk maven gradle

# --- Go (Golang) ---
RUN wget https://go.dev/dl/go1.21.6.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz && \
    rm go1.21.6.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# --- C# (.NET 8 SDK) ---
RUN wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    rm packages-microsoft-prod.deb && \
    apt-get update && \
    apt-get install -y dotnet-sdk-8.0

# --- Rust (Cargo) ---
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# --- PHP 8.1 & Composer ---
RUN apt-get update && apt-get install -y php php-cli php-mbstring unzip && \
    curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

# --- Ruby 3.0 ---
RUN apt-get update && apt-get install -y ruby-full

# Cleanup
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# We don't COPY . here because we inject code at runtime.
# This image is just the TOOLBOX.

CMD ["/bin/bash"]
