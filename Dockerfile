FROM ubuntu:22.04

RUN apt-get update && \
  apt-get install -y net-tools iputils-ping tcpdump ethtool wget iproute2 bridge-utils openvpn build-essential

RUN wget https://downloads.sourceforge.net/project/iperf2/iperf-2.1.9.tar.gz && \
tar xf iperf-2.1.9.tar.gz && cd iperf-2.1.9 && ./configure && make && make install

#RUN wget https://github.com/esnet/iperf/archive/refs/tags/3.13.tar.gz && \
#tar xf 3.13.tar.gz && cd iperf-3.13 && ./configure --enable-static-bin && make && make install

