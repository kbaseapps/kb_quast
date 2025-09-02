FROM kbase/sdkpython:3.8.10
MAINTAINER KBase Developer
# -----------------------------------------
# System deps required to build QUAST bundled tools
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        build-essential perl wget ca-certificates zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Optional: enable static/PDF plots
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     pkg-config libfreetype6-dev libpng-dev python3-matplotlib && \
#     rm -rf /var/lib/apt/lists/*

# -----------------------------------------
# Python tooling (upgrade packaging to avoid canonicalize_version error)
RUN python3 -m pip install -U pip setuptools wheel packaging && python --version

# If you keep these utilities, install them here
RUN pip install coverage==5.5 in_place==1.0.1 pathos==0.3.4

# -----------------------------------------
# Install QUAST 5.3.0 from source (PyPI tops out at 5.2.0)
ENV QUAST_VER=5.3.0
WORKDIR /opt
RUN wget -qO quast-${QUAST_VER}.tar.gz \
      "https://sourceforge.net/projects/quast/files/quast-${QUAST_VER}.tar.gz/download" \
 && tar -xzf quast-${QUAST_VER}.tar.gz \
 && cd quast-${QUAST_VER} \
 && python3 -m pip install . --no-cache-dir --root-user-action=ignore \
 && quast.py --version

RUN pip install biopython==1.81
 
# Python tooling (upgrade packaging, etc.)
RUN python3 -m pip install -U pip setuptools wheel packaging && python --version
# Add psutil (and keep your existing utilities)
RUN pip install psutil coverage==5.5 in_place==1.0.1 pathos==0.3.4

# -----------------------------------------
# Your module
COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module
RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]
CMD [ ]
