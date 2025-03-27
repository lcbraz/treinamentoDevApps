#!/bin/bash

mkdir logs 2>/dev/null

pkill -f 'uvicorn api_conexoes:app'
cd api_conexoes
uvicorn api_conexoes:app --reload --log-config logging.yaml --host 0.0.0.0 --port 9002 > ../logs/api_conexoes.log 2>&1 &


pkill -f 'uvicorn api_pagamentos:app'
cd ../api_pagamentos
uvicorn api_pagamentos:app --reload --log-config logging.yaml --host 0.0.0.0 --port 9001 > ../logs/api_pagamentos.log 2>&1 &


pkill -f 'uvicorn front_usuarios:app'
cd ../front_usuarios
uvicorn front_usuarios:app --reload --log-config logging.yaml --host 0.0.0.0 --port 9000 > ../logs/front_usuarios.log 2>&1 &

