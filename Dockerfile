FROM lambci/lambda:build-python3.7
RUN mkdir /build
WORKDIR /build
RUN python3.7 -m venv /build/venv
ENV VIRTUAL_ENV=/build/venv
ENV PATH=/build/venv/bin:$PATH
COPY requirements.txt /build/
RUN pip3.7 install -r requirements.txt
COPY index.py /build/
RUN zip -9 -q /lambda.zip index.py
WORKDIR /build/venv/lib/python3.7/site-packages
RUN zip -9 -q -u -r /lambda.zip . -x "*.dist-info/" "pylint/" "easy_install.py" "pip/"
WORKDIR /usr
RUN zip -9 -q -u /lambda.zip bin/git bin/ssh lib64/libfipscheck.so.*
VOLUME /export
