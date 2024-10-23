#!/bin/bash

# Переменные
IMAGE_NAME="ytb2audiobot"  # Название вашего образа
REGISTRY="andrewlevin"  # Ваш Docker реестр, например, Docker Hub или локальный реестр

TAG='2.615'

# Построить образ с новым тэгом
docker build -t $REGISTRY/$IMAGE_NAME:$TAG .

# Загрузить образ в реестр (если необходимо)
docker push $REGISTRY/$IMAGE_NAME:$TAG

echo -e "✅ \t $REGISTRY/$IMAGE_NAME:$TAG \t The image has been built and pushed to the registry."