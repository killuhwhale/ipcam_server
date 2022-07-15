# Python version to use
FROM python:3.8.9
# Output sent to terminal, debugging
ENV PYTHONUNBUFFERED 1
# Set workdir in image
WORKDIR /app/api
# Copy from local to image
COPY requirements.txt ./
# CV2 dependencies
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y
# Run cmd on image
RUN python3 -m pip install --upgrade pip

RUN pip install -r requirements.txt
COPY . ./
# Container listenes on this port
EXPOSE 8000