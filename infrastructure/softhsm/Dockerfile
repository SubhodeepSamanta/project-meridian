FROM smallstep/step-ca:hsm@sha256:22e4c0d73b10a031fed40a31d0736c2f4538995da2c083556565dd282a9d2c92

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends softhsm2 opensc \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/lib/softhsm/tokens \
    && printf 'directories.tokendir = /var/lib/softhsm/tokens\nobjectstore.backend = file\n' > /etc/softhsm2.conf

ENV SOFTHSM2_CONF=/etc/softhsm2.conf
