FROM kbase/kbase:sdkbase.latest
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

# RUN apt-get update


RUN apt-get update \
    && apt-get -y install libboost-all-dev

# DO NOT use install_full - downloads the Silva database, which has a non open source license
# As a result cannot use MetaQUAST
# deletes genemark executables, also non open source license
RUN cd /opt \
    && wget https://downloads.sourceforge.net/project/quast/quast-4.4.tar.gz \
    && tar -xzf quast-4.4.tar.gz \
    && cd quast-4.4 \
    && ./setup.py install \
    && rm -r quast_libs/genemark\
    && rm -r quast_libs/genemark-es

RUN pip install ipython==5.3.0 \
    && pip install psutil

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
