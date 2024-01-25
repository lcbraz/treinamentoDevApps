import logging
import logging.config
from datetime import datetime
from typing import List
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
import yaml
from fastapi import FastAPI, HTTPException

from database import engine_auto, text, SQLAlchemyError, OperationalError, NoResultFound


# TDDO Adicionar contexto
f = open('logging.yaml', 'r')
d = yaml.safe_load(f)
f.close()
logging.config.dictConfig(d)
logger = logging.getLogger('app')

app = FastAPI()


################
# API usuarios #
################

class Conexao(BaseModel):
    id: str
    data_inicio: datetime
    data_fim: datetime | None = None
    bytes: int = 0

class ConexaoNovo(BaseModel):
    usuario_id: str

class ConexaoAtualiza(BaseModel):
    id: str
    data_fim: datetime
    bytes: int

class ExcResponse(BaseModel):
    detail: str

@app.get("/api/conexao/{conexao_id}",
         responses={404: {"model": ExcResponse}})
def get_conexao(conexao_id) -> Conexao:
    try:
        with engine_auto.connect() as conn:
            sql = text("SELECT id, data_inicio, data_fim, bytes FROM conexoes WHERE id = :conexao_id").\
                    bindparams(conexao_id=conexao_id)
            result = conn.execute(sql)
            return Conexao(**dict(zip(result.keys(), result.one())))
    except NoResultFound:
        error_msg = "Conexao não encontrada: {conexao_id}"
        logger.info(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/api/conexoes/{usuario_id}")
def list_conexoes(usuario_id) -> List[Conexao]:
    conexoes = []
    try:
        for _ in range(10000):
            conexoes = []
            with engine_auto.connect() as conn:
                sql = text("SELECT id, data_inicio, data_fim, bytes FROM conexoes WHERE usuario_id = :usuario_id").\
                        bindparams(usuario_id=usuario_id)
                result = conn.execute(sql)
                for row in result.all():
                    conexoes.append(dict(list(zip(result.keys(), row))))
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))
    else:
        for row in result.all():
            conexoes.append(dict(list(zip(result.keys(), row))))
    return conexoes


@app.post("/api/conexao",
          responses={400: {"model": ExcResponse}})
def create_conexao(conexao_novo: ConexaoNovo) -> Conexao:
    try:
        with engine_auto.connect() as conn:
            sql = text("INSERT INTO conexoes (usuario_id) VALUES (:usuario_id) \
                    RETURNING id, data_inicio, data_fim, bytes").\
                    bindparams(**conexao_novo.model_dump())
            result = conn.execute(sql)
            return Conexao(**dict(zip(result.keys(), result.one())))
    except IntegrityError as error:
        logger.info(error)
        raise HTTPException(status_code=400, detail="Falha ao criar conexao: {usuario_id}")
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


@app.delete("/api/conexao/{conexao_id}",
            responses={400: {"model": ExcResponse}})
def delete_usuario(conexao_id) -> Conexao:
    try:
        with engine_auto.connect() as conn:
            sql = text("DELETE FROM conexoes WHERE id = :conexao_id \
                    RETURNING id, data_inicio, data_fim, bytes").\
                    bindparams(conexao_id=conexao_id)
            result = conn.execute(sql)
            return Conexao(**dict(zip(result.keys(), result.one())))
    except NoResultFound:
        error_msg = f"Falha ao apagar conexão: {conexao_id}"
        logger.info(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))


@app.put("/api/conexao",
         responses={400: {"model": ExcResponse}})
def update_usuario(conexao_atualiza: ConexaoAtualiza) -> Conexao:
    try:
        with engine_auto.connect() as conn:
            sql = text("UPDATE conexoes SET data_fim = :data_fim, bytes = :bytes WHERE id = :conexao_id").\
                    bindparams(conexao_id=conexao_atualiza.id, data_fim=conexao_atualiza.data_fim, 
                               bytes=conexao_atualiza.bytes)
            conn.execute(sql)
            sql = text("SELECT id, data_inicio, data_fim, bytes FROM conexoes WHERE id = :conexao_id").\
                      bindparams(conexao_id=conexao_atualiza.id)
            result = conn.execute(sql)
            return Conexao(**dict(zip(result.keys(), result.one())))
    except NoResultFound:
        error_msg = f"Falha atualização conexão: {conexao_atualiza.id}"
        logger.info(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except (SQLAlchemyError, OperationalError) as error:
        logger.error(error)
        raise HTTPException(status_code=500, detail=str(error))

