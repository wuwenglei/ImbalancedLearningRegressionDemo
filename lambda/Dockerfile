FROM amazon/aws-lambda-python:3.10

LABEL maintainer="Wenglei Wu"

RUN yum update -y && \
    yum install -y python3 python3-dev python3-pip gcc && \
    rm -Rf /var/cache/yum

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY ./helper/*.py ./helper/

COPY resampling.py ./

CMD ["resampling.lambda_handler"]