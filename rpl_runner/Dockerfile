FROM ubuntu:noble

RUN apt-get update     && \
    apt-get upgrade -y && \
    apt-get install -y gcc gcc-multilib g++ clang      	\
    make valgrind time python3 	\
    python3-dev libgtest-dev       \
    python3-pip python3-venv git curl wget \
    cppcheck pylint

RUN pip3 install --break-system-packages timeout-decorator flask gunicorn pulp && \
    pip3 install --break-system-packages --ignore-installed pydantic

# Install go
RUN wget -q https://go.dev/dl/go1.22.5.linux-amd64.tar.gz && \
    tar -xf go1.22.5.linux-amd64.tar.gz && \
    mv go /usr/lib && \
    rm go1.22.5.linux-amd64.tar.gz

ENV GOROOT /usr/lib/go
ENV GOCACHE /go/cache
ENV GOPATH /go
ENV PATH $GOPATH/bin:$GOROOT/bin:$PATH

RUN go version

# Create usser for main process without root privileges
RUN groupadd -g 2500 runner
RUN useradd -m -u 98989 -g runner -s /bin/bash runner

# Add runner
ADD runner-libs/ /runner-libs/

# Copy libcriterion files
RUN tar -zxvf /runner-libs/c/criterion_rpl_v2.tar.gz -C /runner-libs/c/
RUN cp -r /runner-libs/c/. /usr
RUN cp -r /runner-libs/python/. /usr

COPY ["go.mod", "go.sum", "/"]

# Cache testify dependency
RUN go get github.com/stretchr/testify@v1.7.0

# Cache testify build
RUN go install github.com/stretchr/testify


# Install Rust for root and make it available to the runner user
USER runner
WORKDIR /home/runner

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- --default-toolchain=1.88.0 -y
ENV PATH="/home/runner/.cargo/bin:${PATH}"

RUN /home/runner/.cargo/bin/rustc --version
RUN curl -LsSf https://get.nexte.st/0.9/linux | tar zxf - -C ${CARGO_HOME:-~/.cargo}/bin

USER root
COPY ["nextest.toml", "/"]
RUN mkdir -p /home/runner/.aux_config_cargo
# NEEDED HERE TO AVOID PERMANENT UNDETECTABILITY OF RUST PROJECTS
# if the cargo related toml files are at / cargo will ALWAYS try to compile from there regardless of any parameters or working directory  
COPY ["Cargo.toml", "Cargo.lock", "/home/runner/.aux_config_cargo/"]




COPY ["*.py", "*_Makefile", "/"]
COPY shared/ /shared/

RUN chown -R runner:runner /home/runner
RUN chown -R runner:runner /go

ENV PYTHONUNBUFFERED=TRUE
USER runner

WORKDIR /home/runner
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8000", "--chdir", "/", "--timeout", "60", "init_server:app"]
