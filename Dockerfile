FROM kbase/kbase:sdkbase.latest
MAINTAINER KBase Developer
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.

# RUN apt-get update

RUN cd /opt \
    && wget https://downloads.sourceforge.net/project/quast/quast-4.4.tar.gz \
    && tar -xzf quast-4.4.tar.gz \
    && cd quast-4.4 \
    && ./setup.py install_full

RUN pip install ipython \
    && pip install psutil

RUN apt-get install nano \
    && apt-get install tree

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod 777 /kb/module

WORKDIR /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
