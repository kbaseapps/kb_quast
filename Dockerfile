FROM kbase/sdkpython:3.8.10
LABEL maintainer="KBase Developer"

# -----------------------------------------
# System deps required to build QUAST bundled tools
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        build-essential perl wget ca-certificates zlib1g-dev procps zip && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------------------
# Python tooling
RUN python3 -m pip install -U pip setuptools wheel packaging && python --version
RUN pip install psutil coverage==5.5 in_place==1.0.1 pathos==0.3.4 biopython==1.81

# -----------------------------------------
# QUAST 5.3.0 from source
ENV QUAST_VER=5.3.0
WORKDIR /opt
RUN wget -qO quast-${QUAST_VER}.tar.gz \
      "https://sourceforge.net/projects/quast/files/quast-${QUAST_VER}.tar.gz/download" \
 && tar -xzf quast-${QUAST_VER}.tar.gz \
 && cd quast-${QUAST_VER} \
 && python3 -m pip install . --no-cache-dir --root-user-action=ignore \
 && quast.py --version

# -----------------------------------------
# Bio toolchain for MetaQUAST via micromamba (Bioconda)
ENV MAMBA_ROOT_PREFIX=/opt/conda
RUN wget -qO- https://micro.mamba.pm/api/micromamba/linux-64/latest \
  | tar -xvj -C /usr/local/bin/ --strip-components=1 bin/micromamba
SHELL ["/bin/bash", "-lc"]
RUN micromamba create -y -n quastx -c conda-forge -c bioconda \
      blast=2.14.* minimap2=2.* mummer4=4.* krona && \
    micromamba clean -a -y
ENV PATH=/opt/conda/envs/quastx/bin:$PATH

# -----------------------------------------
# Your module
WORKDIR /kb/module
COPY ./ /kb/module
RUN mkdir -p /kb/module/work && chmod -R a+rw /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]
CMD [ ]
