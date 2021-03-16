FROM centos:7

RUN yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm && \
    yum install -y pugixml && \
    yum install -y python3 && \
    yum install -y make rpm-build git-core erlang gcc-c++ boost-devel pugixml-devel python3-devel && \
    git clone --depth=1 -b v2.8.0 --recurse-submodules https://github.com/ipbus/ipbus-software.git && \
    cd ipbus-software && \
    make Set=uhal PYTHON=python3 && \
    make install Set=uhal PYTHON=python3 && \
    export LD_LIBRARY_PATH=/opt/cactus/lib:$LD_LIBRARY_PATH

COPY . /tamalero
WORKDIR /tamalero
