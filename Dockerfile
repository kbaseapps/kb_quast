FROM kbase/sdkpython:3.8.10
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

RUN apt update && apt install -y  g++ nano tree

RUN python -m pip install --upgrade pip \
    && pip install \
            psutil==6.0.0 \
            matplotlib==3.7.5 \
            quast==5.2.0 \
            biopython==1.83 \
    && rm -r /opt/conda3/lib/python3.8/site-packages/quast_libs/genemark \
    && rm -r /opt/conda3/lib/python3.8/site-packages/quast_libs/genemark-es

# Genemark is not open source for non-academic use, and so can't be used in KBase

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R 777 /kb/module

WORKDIR /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
