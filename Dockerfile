FROM kbase/sdkbase2:python
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

# RUN apt-get update


RUN apt-get update \
    && apt-get -y install libboost-all-dev \
    && apt-get -y install wget \
    && apt-get -y install g++

RUN python -m pip install --upgrade pip \
    && pip install psutil \
    && pip install matplotlib

# DO NOT use install_full - downloads the Silva database, which has a non open source license
# As a result cannot use MetaQUAST
# deletes genemark executables, also non open source license
RUN cd /opt \
    && wget https://github.com/ablab/quast/releases/download/quast_5.0.2/quast-5.0.2.tar.gz \
    && tar -xzf quast-5.0.2.tar.gz \
    && cd quast-5.0.2 \
    && ./setup.py install \
    && rm -r quast_libs/genemark\
    && rm -r quast_libs/genemark-es

RUN apt-get install nano \
    && apt-get install tree

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R 777 /kb/module

WORKDIR /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
