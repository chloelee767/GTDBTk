# docker build --build-arg VER=1.6.0 --no-cache -t lee0767/gtdbtk-ubuntu16:1.6.0 .

# How to build and deploy the Docker image:
# docker build --build-arg VER=1.2.3 --no-cache -t ecogenomic/gtdbtk:latest -t ecogenomic/gtdbtk:1.2.3 .
# docker push ecogenomic/gtdbtk:latest && sudo docker push ecogenomic/gtdbtk:1.2.3

FROM ubuntu:16.04

ARG VER

# ---------------------------------------------------------------------------- #
# --------------------- INSTALL HMMER, PYTHON3, FASTTREE---------------------- #
# ---------------------------------------------------------------------------- #
RUN apt-get update -y -m && \
    # adds add-apt-repository command
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \ # python ppa

    apt-get update -y -m && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
                                               wget \
                                               libgomp1 \
                                               hmmer=3.1b2-2 \
                                               prodigal=1:2.6.2-2 \
                                               fasttree=2.1.8-2 \
                                               unzip \
                                               python3.8 \
                                               python3-setuptools \
                                               python3-wheel \
    # Fix ImportError: cannot import name 'sysconfig' from 'distutils' (/usr/lib/python3.8/distutils/__init__.py)
                                               python3.8-distutils && \

    # Fix AttributeError: module 'platform' has no attribute 'linux_distribution'
    # python3.8 -m easy_install pip && \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3.8 get-pip.py && \

    # install mash
    wget https://github.com/marbl/Mash/releases/download/v2.0/mash-Linux64-v2.0.tar && \
    tar xf mash-Linux64-v2.0.tar && \
    mv mash-Linux64-v2.0/mash /usr/bin && \
    rm -r mash-Linux64-v2.0.tar mash-Linux64-v2.0 && \

    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    ln -s /usr/bin/fasttree /usr/bin/FastTree && \
    ln -s /usr/bin/fasttreeMP /usr/bin/FastTreeMP

# ---------------------------------------------------------------------------- #
# ------------------------------ ALIAS PYTHON3  ------------------------------ #
# ---------------------------------------------------------------------------- #
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.8 1 && \
    update-alternatives --set python /usr/bin/python3.8

# ---------------------------------------------------------------------------- #
# ----------------------------- INSTALL PPLACER ------------------------------ #
# ---------------------------------------------------------------------------- #
RUN wget https://github.com/matsen/pplacer/releases/download/v1.1.alpha19/pplacer-linux-v1.1.alpha19.zip -q && \
    unzip pplacer-linux-v1.1.alpha19.zip && \
    mv pplacer-Linux-v1.1.alpha19/* /usr/bin && \
    rm pplacer-linux-v1.1.alpha19.zip && \
    rm -rf pplacer-Linux-v1.1.alpha19

# ---------------------------------------------------------------------------- #
# ----------------------------- INSTALL FASTANI ------------------------------ #
# ---------------------------------------------------------------------------- #
RUN wget https://github.com/ParBLiSS/FastANI/releases/download/v1.32/fastANI-Linux64-v1.32.zip -q && \
    unzip fastANI-Linux64-v1.32.zip -d /usr/bin && \
    rm fastANI-Linux64-v1.32.zip

# ---------------------------------------------------------------------------- #
# --------------------- SET GTDB-TK MOUNTED DIRECTORIES ---------------------- #
# ---------------------------------------------------------------------------- #
RUN mkdir /refdata && \
    mkdir /data
ENV GTDBTK_DATA_PATH="/refdata/"

# ---------------------------------------------------------------------------- #
# --------------------------- INSTALL PIP PACKAGES --------------------------- #
# ---------------------------------------------------------------------------- #
RUN python -m pip install --upgrade pip && \
    python -m pip install gtdbtk==${VER}

# ---------------------------------------------------------------------------- #
# ---------------------------- SET THE ENTRYPOINT ---------------------------- #
# ---------------------------------------------------------------------------- #
ENTRYPOINT ["gtdbtk"]
CMD ["--help"]
